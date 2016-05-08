#!/usr/bin/env python

"""models.py

Udacity meeting server-side Python App Engine data & ProtoRPC models

$Id: models.py,v 1.1 2014/05/24 22:01:10 wesc Exp $

created/forked from meetings.py by wesc on 2014 may 24

"""

__author__ = 'wesc+api@google.com (Wesley Chun)'

import httplib
import endpoints
from protorpc import messages
from google.appengine.ext import ndb


class Profile(ndb.Model):
    """Profile -- User profile object"""
    userId       = ndb.StringProperty()
    displayName  = ndb.StringProperty()
    mainEmail    = ndb.StringProperty()
    teeShirtSize = ndb.StringProperty(default='NOT_SPECIFIED')


class ProfileMiniForm(messages.Message):
    """ProfileMiniForm -- update Profile form message"""
    # Contains only the fields editable by users
    displayName  = messages.StringField(1)
    teeShirtSize = messages.EnumField('TeeShirtSize', 2)


class ProfileForm(messages.Message):
    """ProfileForm -- Profile outbound form message"""
    userId       = messages.StringField(1)
    displayName  = messages.StringField(2)
    mainEmail    = messages.StringField(3)
    teeShirtSize = messages.EnumField('TeeShirtSize', 4)


class TeeShirtSize(messages.Enum):
    """TeeShirtSize -- t-shirt size enumeration value"""
    # Because we don't want users to put in arbitrary values,
    # enum is used. Expected input is text (example: 'XS_M').
    NOT_SPECIFIED = 1
    XS_M   = 2
    XS_W   = 3
    S_M    = 4
    S_W    = 5
    M_M    = 6
    M_W    = 7
    L_M    = 8
    L_W    = 9
    XL_M   = 10
    XL_W   = 11
    XXL_M  = 12
    XXL_W  = 13
    XXXL_M = 14
    XXXL_W = 15


class Meeting(ndb.Model):
    """Meeting -- Meeting object"""
    name            = ndb.StringProperty(required=True)
    description     = ndb.StringProperty()
    organizerUserId = ndb.StringProperty()
    topics          = ndb.StringProperty(repeated=True)
    city            = ndb.StringProperty()
    startDate       = ndb.DateProperty()
    month           = ndb.IntegerProperty()
    endDate         = ndb.DateProperty()
    maxAttendees    = ndb.IntegerProperty()
    seatsAvailable  = ndb.IntegerProperty()


class MeetingForm(messages.Message):
    """MeetingForm == Meeting outbound form message"""
    name            = messages.StringField(1)
    description     = messages.StringField(2)
    organizerUserId = messages.StringField(3)
    topics          = messages.StringField(4, repeated=True)
    city            = messages.StringField(5)
    startDate       = messages.StringField(6)
    month           = messages.StringField(7)
    endDate         = messages.StringField(8)
    maxAttendees    = messages.StringField(9)
    seatsAvailable  = messages.StringField(10)
    webSafeKey      = messages.StringField(11)
    organizerDisplayName = messages.StringField(12)
