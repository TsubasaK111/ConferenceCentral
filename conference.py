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
from utils import getUserId
from settings import WEB_CLIENT_ID

import pdb

EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID


@endpoints.api( name='conference', version='v1', scopes=[EMAIL_SCOPE],
                allowed_client_ids=[WEB_CLIENT_ID, API_EXPLORER_CLIENT_ID] )
class ConferenceApi(remote.Service):
    """Conference API v0.1"""

    # - - - Helper Functions - - - - - - - - - - - - - - - - - - -
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
        print "user_id is: "
        print user_id
        print dir(user_id)
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
            # save profile to datastore
            profile.put()
            # returned_profile_key = profile.put()
            print "returned_profile_key is: "
            print returned_profile_key
        return profile

    def _doProfile(self, save_request=None):
        """Get user Profile and return to user, possibly updating it first."""
        # get user Profile
        profile = self._getProfileFromUser()
        # if saveProfile(), process user-modifiable fields
        if save_request:
            print "save_request! "
            for field in ('displayName', 'teeShirtSize'):
                if hasattr(save_request, field):
                    value = getattr(save_request, field)
                    if value:
                        print "setting attr in _doProfile!"
                        setattr(profile, field, str(value))
            profile.put()
            
        # return the ProfileForm
        print "in _doProfile, profile is: "
        print profile
        return self._copyProfileToForm(profile)


    # - - - Endpoint Routing  - - - - - - - - - - - - - - - - - - -
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


# registers API
api = endpoints.api_server([ConferenceApi])
