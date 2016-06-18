#!/usr/bin/env python

"""
conference.py -- Udacity conference server-side Python App Engine API;
    uses Google Cloud Endpoints

$Id: conference.py,v 1.25 2014/05/24 23:42:19 wesc Exp wesc $

created by wesc on 2014 apr 21

"""

__author__ = 'wesc+api@google.com (Wesley Chun)'

from datetime import datetime
import json
import os
import time

import endpoints
from protorpc import messages, message_types, remote

from google.appengine.api import taskqueue
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.ext import ndb

from models import Profile, ProfileMiniForm, ProfileForm, TeeShirtSize
from models import Conference, ConferenceForm, ConferenceForms, ConferenceQueryForm, ConferenceQueryForms
from models import BooleanMessage, ConflictException, StringMessage

from utils import getUserId

from settings import WEB_CLIENT_ID, FRONTING_WEB_CLIENT_ID

import pdb, logging


EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID
MEMCACHE_ANNOUNCEMENTS_KEY = "announcements"
MEETING_DEFAULTS = { "city": "Default City",
                     "maxAttendees": 0,
                     "seatsAvailable": 0,
                     "topics": [ "Default", "Topic" ], }

OPERATORS = { 'EQ':   '=',
              'GT':   '>',
              'GTEQ': '>=',
              'LT':   '<',
              'LTEQ': '<=',
              'NE':   '!=' }

FIELDS =    { 'CITY': 'city',
              'TOPIC': 'topics',
              'MONTH': 'month',
              'MAX_ATTENDEES': 'maxAttendees', }

CONF_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    webSafeKey=messages.StringField(1),
)

@endpoints.api( name='conference', version='v1', scopes=[EMAIL_SCOPE],
                allowed_client_ids=[ WEB_CLIENT_ID,
                                     FRONTING_WEB_CLIENT_ID,
                                     API_EXPLORER_CLIENT_ID ], )
class ConferenceApi(remote.Service):
    """Conference API v0.1"""

# - - - Profile Objects - - - - - - - - - - - - - - - - - - -
    def _copyProfileToForm(self, profile):
        """Copy relevant fields from Profile to ProfileForm."""
        profileForm = ProfileForm()
        for field in profileForm.all_fields():
            if hasattr(profile, field.name):
                # convert t-shirt string to Enum; just copy others
                if field.name == 'teeShirtSize':
                    setattr( profileForm,
                             field.name,
                             getattr(TeeShirtSize, getattr(profile, field.name)) )
                else:
                    setattr( profileForm,
                             field.name,
                             getattr(profile, field.name) )
        profileForm.check_initialized()
        return profileForm

    def _getProfileFromUser(self):
        """Return user Profile from datastore, creating new one if non-existent."""
        # step 1: make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        # get user id by calling getUserId(user)
        user_id = getUserId(user)
        logging.debug( "user_id is: " )
        logging.debug( user_id )

        # create a new key of kind Profile from the id
        profile_key = ndb.Key(Profile, user_id)
        # get entity from datastore by using get() on the key
        profile = profile_key.get()

        # create a new Profile from logged in user data
        # use user.nickname() to get displayName
        # and user.email() to get mainEmail
        if not profile:
            profile = Profile(
                userId       = None,
                key          = profile_key,
                displayName  = user.nickname(),
                mainEmail    = user.email(),
                teeShirtSize = str(TeeShirtSize.NOT_SPECIFIED),
            )
            # save new profile to datastore
            returned_profile_key = profile.put()
            print "returned_profile_key is: "
            print returned_profile_key
        return profile

    def _doProfile(self, save_request=None):
        """Get user Profile and return to user, possibly updating it first."""
        # get user Profile
        profile = self._getProfileFromUser()
        # if saveProfile(), process user-modifiable fields
        if save_request:
            print "save_request!"
            for field in ('displayName', 'teeShirtSize'):
                if hasattr(save_request, field):
                    value = getattr(save_request, field)
                    if value:
                        print "setting attr in _doProfile!"
                        setattr(profile, field, str(value))
            # remember, you have to .put() to finalize any changes made!^^
            profile.put()

        # return the ProfileForm
        print "in _doProfile, profile is: "
        print profile
        return self._copyProfileToForm(profile)

# - - - Profile Endpoints - - - - - - - - - - - - - -
    @endpoints.method( message_types.VoidMessage, ProfileForm,
                       path='profile', http_method='GET', name='getProfile' )
    def getProfile(self, request):
        """Return user profile."""
        return self._doProfile()

    @endpoints.method( ProfileMiniForm, ProfileForm,
                   path='profile', http_method='POST', name='saveProfile' )
    def saveProfile(self, request):
        """Update & return user profile."""
        # request contains only fields in the ProfileMiniForm.
        # Pass this to _doProfile function, which will return profile info
        # from the datastore.
        print request
        return self._doProfile(request)

# - - - Conference Objects - - - - - - - - - - - - - -
    def _createConferenceObject(self, request):
        """Create or update Conference object, returning ConferenceForm/request."""
        # guard clauses / load prerequisites
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        if not request.name:
            raise endpoints.BadRequestException("Conference 'name' field required!")

        # Oh gawd, dict comprehensions! :(
        # Copy ConferenceForm/ProtoRPC Message into 'data' dict
        data = {
            field.name: getattr(request, field.name) for field in request.all_fields()
            }
        del data['webSafeKey']
        del data['organizerDisplayName']

        logging.debug( "data was: " )
        logging.debug( data )
        # add default values for those mission (both data model & outbound Message)
        for default in MEETING_DEFAULTS:
            if data[default] in (None, []):
                data[default] = MEETING_DEFAULTS[default]
                setattr(request, default, MEETING_DEFAULTS[default])

        # convert dates from strings to Date objects; set month based on start_date
        if data['startDate']:
            data['startDate'] = datetime.strptime(data['startDate'][:10], "%Y-%m-%d").date()
            data['month'] = data['startDate'].month
        else:
            data['month'] = 0
        if data['endDate']:
            data['endDate'] = datetime.strptime(data['endDate'][:10], "%Y-%m-%d").date()

        # set seatsAvailable to be the same as maxAtendees on creation
        # both for data model & outbound Message
        if data['maxAttendees'] > 0:
            data['seatsAvailable'] = data['maxAttendees']
            setattr(request, "seatsAvailable", data["maxAttendees"] )

        # make key from user ID
        profile_key = ndb.Key(Profile, user_id)

        # arbitrarily create new, unique id via ndb.model.alloc
        conference_id = Conference.allocate_ids(size=1, parent=profile_key)[0]

        # create a new key of kind Conference from the profile_key
        conference_key = ndb.Key(Conference, conference_id, parent=profile_key)

        data['key'] = conference_key
        data['organizerUserId'] = request.organizerUserId = user_id

        logging.debug( "data is: " )
        logging.debug( data )

        # create Conference & return modified ConferenceForm
        Conference(**data).put()
        taskqueue.add(
            params={
                'email': user.email(),
                'conferenceInfo': repr(request)
            },
            url='/tasks/send_confirmation_email'
        )

        return request

    def _copyConferenceToForm(self, conference, displayName):
        """Copy relevant fields from Conference to ConferenceForm"""
        conferenceForm = ConferenceForm()

        for field in conferenceForm.all_fields():
            logging.debug("field name is: "+field.name)
            if hasattr(conference, field.name):
                # convert Date to date string: just copy others
                if field.name.endswith('Date'):
                    setattr(conferenceForm, field.name, str(getattr(conference, field.name)))
                else:
                    setattr(conferenceForm, field.name, getattr(conference, field.name))
            elif field.name == "webSafeKey":
                setattr(conferenceForm, field.name, conference.key.urlsafe())
            if displayName:
                setattr(conferenceForm, "organizerDisplayName", displayName)

        logging.info( "conferenceForm is: " )
        logging.info( conferenceForm )
        conferenceForm.check_initialized()
        return conferenceForm

# - - - Querying Helper Methods - - - - - - - - - - - - - -
    def _getQuery(self, request):
        """Return formatted query from the submitted filters."""
        conferences = Conference.query()
        inequality_filter, filters = self._formatFilters(request.filters)

        # If exists, sort on inequality filter first
        if not inequality_filter:
            conferences = conferences.order(Conference.name)
        else:
            conferences = conferences.\
                order(ndb.GenericProperty(inequality_filter)).\
                order(Conference.name)

        for filtre in filters:
            if filtre["field"] in ["month", "maxAttendees"]:
                filtre["value"] = int(filtre["value"])
            formatted_query = ndb.query.FilterNode( filtre["field"],
                                                    filtre["operator"],
                                                    filtre["value"] )
            conferences = conferences.filter(formatted_query)
        return conferences


    def _formatFilters(self, filters):
        """Parse, check validity and format user supplied filters."""
        formatted_filters = []
        inequality_field = None

        for f in filters:
            filtre = {field.name: getattr(f, field.name) for field in f.all_fields()}

            try:
                filtre["field"] = FIELDS[filtre["field"]]
                filtre["operator"] = OPERATORS[filtre["operator"]]
            except KeyError:
                raise endpoints.BadRequestException("Filter contains invalid field or operator.")

            # Every operation except "=" is an inequality
            if filtre["operator"] != "=":
                # check if inequality operation has been used in previous filters
                # disallow the filter if inequality was performed on a different field before
                # track the field on which the inequality operation is performed
                if inequality_field and inequality_field != filtre["field"]:
                    raise endpoints.BadRequestException("Inequality filter is allowed on only one field.")
                else:
                    inequality_field = filtre["field"]

            formatted_filters.append(filtre)
        return (inequality_field, formatted_filters)

# - - - Conference Endpoints - - - - - - - - - - - - - -
    @endpoints.method( ConferenceForm, ConferenceForm,
                       path='conference', http_method='POST', name='createConference' )
    def createConference(self, request):
        """Create new conference."""
        return self._createConferenceObject(request)

    @endpoints.method( ConferenceQueryForms, ConferenceForms,
                       path='queryConferences',
                       http_method='POST',
                       name='queryConferences' )
    def queryConferences(self, request):
        """Query for conferences."""
        conferences = self._getQuery(request)

        # fetch organizer displayName from profiles to return full ConferenceForms.
        organizers = [ (ndb.Key(Profile, conference.organizerUserId)) \
                        for conference in conferences
                     ]
        profiles = ndb.get_multi(organizers)

        names = {}
        for profile in profiles:
            names[profile.key.id()] = profile.displayName

        # return individual ConferenceForm object per Conference
        # (another dict comprehension!)
        return ConferenceForms(
            items = [ self._copyConferenceToForm(
                            conference,
                            names[conference.organizerUserId]
                        ) for conference in conferences
                    ]
        )

    @endpoints.method( message_types.VoidMessage, ConferenceForms,
                      path="getConferencesCreated",
                      http_method="POST",
                      name="getConferencesCreated" )
    def getConferencesCreated(self, request):
        # guard clauses / load prerequisites
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)
        ### They call this an "ancestor/descendant query":
        conferencesOfUser = Conference.query(ancestor=ndb.Key(Profile, user_id))
        return ConferenceForms(
            items = [ self._copyConferenceToForm(conference, "") \
                      for conference in conferencesOfUser
                    ]
        )

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
            path='conferences/attending',
            http_method='GET', name='getConferencesToAttend')
    def getConferencesToAttend(self, request):
        """Get list of conferences that user has registered for."""
        # TODO:
        # step 1: get user profile
        profile = self._getProfileFromUser()

        # step 2: get conferenceKeysToAttend from profile.
        # to make a ndb key from webSafe key you can use:
        # ndb.Key(urlsafe=my_websafe_key_string)
        webSafeConferenceKeys = profile.conferenceKeysToAttend

        conferenceKeys = []
        for webSafeKey in webSafeConferenceKeys:
            conferenceKeys.append(ndb.Key(urlsafe=webSafeKey))

        # step 3: fetch conferences from datastore.
        # Use get_multi(array_of_keys) to fetch all keys at once.
        # Do not fetch them one by one!
        conferences = ndb.get_multi(conferenceKeys)

        # return set of ConferenceForm objects per Conference
        return ConferenceForms(
            items = [ self._copyConferenceToForm(conference, "") \
                    for conference in conferences ]
        )

    @endpoints.method( message_types.VoidMessage, ConferenceForms,
                       path="filterPlayground",
                       http_method="POST",
                       name="filterPlayground" )
    def filterPlayground(self, request):
        ## Simple syntax for a filter query
        filteredConferences = Conference.query(Conference.city == "London")

        ## AND syntax with sortBy
        # filteredConferences = Conference.query(
        #                         ndb.AND(
        #                             Conference.city == "London",
        #                             Conference.topics == "Medical Innovations"
        #                         )).order(
        #                             Conference.maxAttendees
        #                         ).filter(
        #                             Conference.month == 6
        #                         ).filter(
        #                             Conference.maxAttendees > 10
        #                         )
        return ConferenceForms(
            items = [ self._copyConferenceToForm( conference, "" ) \
                      for conference in filteredConferences
                    ]
        )

# - - - Registration - - - - - - - - - - - - - - - - - - - -
    @ndb.transactional(xg=True)
    def _conferenceRegistration(self, request, register=True):
        """Register or unregister user for selected conference."""
        returnValue = None
        profile = self._getProfileFromUser() # get user Profile

        # check if conference exists given webSafeConfKey
        # get conference; check that it exists
        conferenceKey = request.webSafeKey
        conference = ndb.Key(urlsafe=conferenceKey).get()
        if not conference:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % conferenceKey)

        # register
        if register:
            # check if user already registered otherwise add
            if conferenceKey in profile.conferenceKeysToAttend:
                raise ConflictException(
                    "You have already registered for this conference")

            # check if seats available
            if conference.seatsAvailable <= 0:
                raise ConflictException(
                    "There are no seats available.")

            # register user, take away one seat
            profile.conferenceKeysToAttend.append(conferenceKey)
            conference.seatsAvailable -= 1
            returnValue = True

        # unregister
        else:
            # check if user already registered
            if conferenceKey in profile.conferenceKeysToAttend:

                # unregister user, add back one seat
                profile.conferenceKeysToAttend.remove(conferenceKey)
                conference.seatsAvailable += 1
                returnValue = True
            else:
                returnValue = False

        # write things back to the datastore & return
        profile.put()
        conference.put()
        return BooleanMessage(data=returnValue)

    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
            path='conference/{webSafeKey}/register',
            http_method='POST', name='registerForConference')
    def registerForConference(self, request):
        """Register user for selected conference."""
        return self._conferenceRegistration(request)

    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
            path='conference/{webSafeKey}/unregister',
            http_method='POST', name='unregisterFromConference')
    def unregisterFromConference(self, request):
        """Unregister user from selected registered conference."""
        return self._conferenceRegistration(request, register = False)

# - - - Announcements - - - - - - - - - - - - - - - - - - - -
    @staticmethod
    def _cacheAnnouncement():
        """Create Announcement & assign to memcache;
        used by memcache cron job & putAnnouncement(). """
        nearSoldOutConferences = Conference.query(ndb.AND(
            Conference.seatsAvailable <= 5,
            Conference.seatsAvailable > 0
        )).fetch(
            projection = [Conference.name]
        )

        if nearSoldOutConferences:
            # format announcement and set it in memcache.
            announcement = """Last chance to attend! The following conferences
                are nearly sold out:
                {nearSoldOutConferences}""".format(
                    nearSoldOutConferences = ", ".join(
                        c.name for c in nearSoldOutConferences
                    )
                )
            memcache.set(MEMCACHE_ANNOUNCEMENTS_KEY, announcement)
        else:
            # delete the memcache annoucements entry.
            announcement = ""
            memcache.delete(MEMCACHE_ANNOUNCEMENTS_KEY)

        return announcement

    @endpoints.method(message_types.VoidMessage, StringMessage,
        path='conference/announcement/get',
        http_method='GET', name='getAnnouncement')
    def getAnnouncement(self, request):
        """Return Announcement from memcache."""
        # TODO 1
        # return an existing announcement from memcache OR an empty string.
        announcement = memcache.get(MEMCACHE_ANNOUNCEMENTS_KEY)
        if not announcement:
            announcement = ""
        return StringMessage(data=announcement)

# registers API
api = endpoints.api_server([ConferenceApi])
