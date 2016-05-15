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

from google.appengine.api import urlfetch
from google.appengine.ext import ndb

from models import Profile, ProfileMiniForm, ProfileForm, TeeShirtSize
from models import Conference, ConferenceForm, ConferenceForms, ConferenceQueryForm, ConferenceQueryForms

from utils import getUserId

from settings import WEB_CLIENT_ID, FRONTING_WEB_CLIENT_ID

import pdb, logging


EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID
MEETING_DEFAULTS = { "city": "Default City",
                     "maxAttendees": 0,
                     "seatsAvailable": 0,
                     "topics": [ "Default", "Topic" ], }


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
                elif field.name == "webSafeKey":
                    setattr(conferenceForm, field.name, conference.key.urlsafe())
                else:
                    setattr(conferenceForm, field.name, getattr(conference, field.name))
            if displayName:
                setattr(conferenceForm, "organizerDisplayName", displayName)

        logging.info( "conferenceForm is: " )
        logging.info( conferenceForm )
        conferenceForm.check_initialized()
        return conferenceForm

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
        conferences = Conference.query()

        ##  return individual ConferenceForm object per Conference
        ## (another dict comprehension!)
        return ConferenceForms(
            items=[ self._copyConferenceToForm(conference, "") \
                    for conference in conferences
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

    @endpoints.method( message_types.VoidMessage, ConferenceForms,
                       path="filterPlayground",
                       http_method="POST",
                       name="filterPlayground" )
    def filterPlayground(self, request):
        ## Simple syntax for a filter query
        # filteredConferences = Conference.query(Conference.city == "London")

        ## AND syntax with SORTBY
        filteredConferences = Conference.query(
                                ndb.AND(
                                    Conference.city == "London",
                                    Conference.topics == "Medical Innovations"
                                )).order(
                                    Conference.maxAttendees
                                ).filter(
                                    Conference.month == 6
                                ).filter(
                                    Conference.maxAttendees > 10
                                )


        return ConferenceForms(
            items = [ self._copyConferenceToForm( conference, "" ) \
                      for conference in filteredConferences
                    ]
        )


# registers API
api = endpoints.api_server([ConferenceApi])
