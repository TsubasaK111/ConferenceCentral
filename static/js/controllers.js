'use strict';

/**
 * The root meetingApp module.
 *
 * @type {meetingApp|*|{}}
 */
var meetingApp = meetingApp || {};

/**
 * @ngdoc module
 * @name meetingControllers
 *
 * @description
 * Angular module for controllers.
 *
 */
meetingApp.controllers = angular.module('meetingControllers', ['ui.bootstrap']);

/**
 * @ngdoc controller
 * @name MyProfileCtrl
 *
 * @description
 * A controller used for the My Profile page.
 */
meetingApp.controllers.controller('MyProfileCtrl',
    function ($scope, $log, oauth2Provider, HTTP_ERRORS) {
        $scope.submitted = false;
        $scope.loading = false;

        /**
         * The initial profile retrieved from the server to know the dirty state.
         * @type {{}}
         */
        $scope.initialProfile = {};

        /**
         * Candidates for the teeShirtSize select box.
         * @type {string[]}
         */
        $scope.teeShirtSizes = [
            {'size': 'XS_M', 'text': "XS - Men's"},
            {'size': 'XS_W', 'text': "XS - Women's"},
            {'size': 'S_M', 'text': "S - Men's"},
            {'size': 'S_W', 'text': "S - Women's"},
            {'size': 'M_M', 'text': "M - Men's"},
            {'size': 'M_W', 'text': "M - Women's"},
            {'size': 'L_M', 'text': "L - Men's"},
            {'size': 'L_W', 'text': "L - Women's"},
            {'size': 'XL_M', 'text': "XL - Men's"},
            {'size': 'XL_W', 'text': "XL - Women's"},
            {'size': 'XXL_M', 'text': "XXL - Men's"},
            {'size': 'XXL_W', 'text': "XXL - Women's"},
            {'size': 'XXXL_M', 'text': "XXXL - Men's"},
            {'size': 'XXXL_W', 'text': "XXXL - Women's"}
        ];
        /**
         * Initializes the My profile page.
         * Update the profile if the user's profile has been stored.
         */
        $scope.init = function () {
            var retrieveProfileCallback = function () {
                $scope.profile = {};
                $scope.loading = true;
                gapi.client.meeting.getProfile().
                    execute(function (resp) {
                        $scope.$apply(function () {
                            $scope.loading = false;
                            if (resp.error) {
                                // Failed to get a user profile.
                            } else {
                                // Succeeded to get the user profile.
                                $scope.profile.displayName = resp.result.displayName;
                                $scope.profile.teeShirtSize = resp.result.teeShirtSize;
                                $scope.initialProfile = resp.result;
                            }
                        });
                    }
                );
            };
            if (!oauth2Provider.signedIn) {
                var modalInstance = oauth2Provider.showLoginModal();
                modalInstance.result.then(retrieveProfileCallback);
            } else {
                retrieveProfileCallback();
            }
        };

        /**
         * Invokes the meeting.saveProfile API.
         *
         */
        $scope.saveProfile = function () {
            $scope.submitted = true;
            $scope.loading = true;
            gapi.client.meeting.saveProfile($scope.profile).
                execute(function (resp) {
                    $scope.$apply(function () {
                        $scope.loading = false;
                        if (resp.error) {
                            // The request has failed.
                            var errorMessage = resp.error.message || '';
                            $scope.messages = 'Failed to update a profile : ' + errorMessage;
                            $scope.alertStatus = 'warning';
                            $log.error($scope.messages + 'Profile : ' + JSON.stringify($scope.profile));

                            if (resp.code && resp.code == HTTP_ERRORS.UNAUTHORIZED) {
                                oauth2Provider.showLoginModal();
                                return;
                            }
                        } else {
                            // The request has succeeded.
                            $scope.messages = 'The profile has been updated';
                            $scope.alertStatus = 'success';
                            $scope.submitted = false;
                            $scope.initialProfile = {
                                displayName: $scope.profile.displayName,
                                teeShirtSize: $scope.profile.teeShirtSize
                            };

                            $log.info($scope.messages + JSON.stringify(resp.result));
                        }
                    });
                });
        };
    })
;

/**
 * @ngdoc controller
 * @name CreateMeetingCtrl
 *
 * @description
 * A controller used for the Create meetings page.
 */
meetingApp.controllers.controller('CreateMeetingCtrl',
    function ($scope, $log, oauth2Provider, HTTP_ERRORS) {

        /**
         * The meeting object being edited in the page.
         * @type {{}|*}
         */
        $scope.meeting = $scope.meeting || {};

        /**
         * Holds the default values for the input candidates for city select.
         * @type {string[]}
         */
        $scope.cities = [
            'Chicago',
            'London',
            'Paris',
            'San Francisco',
            'Tokyo'
        ];

        /**
         * Holds the default values for the input candidates for topics select.
         * @type {string[]}
         */
        $scope.topics = [
            'Medical Innovations',
            'Programming Languages',
            'Web Technologies',
            'Movie Making',
            'Health and Nutrition'
        ];

        /**
         * Tests if the arugment is an integer and not negative.
         * @returns {boolean} true if the argument is an integer, false otherwise.
         */
        $scope.isValidMaxAttendees = function () {
            if (!$scope.meeting.maxAttendees || $scope.meeting.maxAttendees.length == 0) {
                return true;
            }
            return /^[\d]+$/.test($scope.meeting.maxAttendees) && $scope.meeting.maxAttendees >= 0;
        }

        /**
         * Tests if the meeting.startDate and meeting.endDate are valid.
         * @returns {boolean} true if the dates are valid, false otherwise.
         */
        $scope.isValidDates = function () {
            if (!$scope.meeting.startDate && !$scope.meeting.endDate) {
                return true;
            }
            if ($scope.meeting.startDate && !$scope.meeting.endDate) {
                return true;
            }
            return $scope.meeting.startDate <= $scope.meeting.endDate;
        }

        /**
         * Tests if $scope.meeting is valid.
         * @param meetingForm the form object from the create_meetings.html page.
         * @returns {boolean|*} true if valid, false otherwise.
         */
        $scope.isValidMeeting = function (meetingForm) {
            return !meetingForm.$invalid &&
                $scope.isValidMaxAttendees() &&
                $scope.isValidDates();
        }

        /**
         * Invokes the meeting.createMeeting API.
         *
         * @param meetingForm the form object.
         */
        $scope.createMeeting = function (meetingForm) {
            if (!$scope.isValidMeeting(meetingForm)) {
                return;
            }

            $scope.loading = true;
            gapi.client.meeting.createMeeting($scope.meeting).
                execute(function (resp) {
                    $scope.$apply(function () {
                        $scope.loading = false;
                        if (resp.error) {
                            // The request has failed.
                            var errorMessage = resp.error.message || '';
                            $scope.messages = 'Failed to create a meeting : ' + errorMessage;
                            $scope.alertStatus = 'warning';
                            $log.error($scope.messages + ' Meeting : ' + JSON.stringify($scope.meeting));

                            if (resp.code && resp.code == HTTP_ERRORS.UNAUTHORIZED) {
                                oauth2Provider.showLoginModal();
                                return;
                            }
                        } else {
                            // The request has succeeded.
                            $scope.messages = 'The meeting has been created : ' + resp.result.name;
                            $scope.alertStatus = 'success';
                            $scope.submitted = false;
                            $scope.meeting = {};
                            $log.info($scope.messages + ' : ' + JSON.stringify(resp.result));
                        }
                    });
                });
        };
    });

/**
 * @ngdoc controller
 * @name ShowMeetingCtrl
 *
 * @description
 * A controller used for the Show meetings page.
 */
meetingApp.controllers.controller('ShowMeetingCtrl', function ($scope, $log, oauth2Provider, HTTP_ERRORS) {

    /**
     * Holds the status if the query is being executed.
     * @type {boolean}
     */
    $scope.submitted = false;

    $scope.selectedTab = 'ALL';

    /**
     * Holds the filters that will be applied when queryMeetingsAll is invoked.
     * @type {Array}
     */
    $scope.filters = [
    ];

    $scope.filtereableFields = [
        {enumValue: 'CITY', displayName: 'City'},
        {enumValue: 'TOPIC', displayName: 'Topic'},
        {enumValue: 'MONTH', displayName: 'Start month'},
        {enumValue: 'MAX_ATTENDEES', displayName: 'Max Attendees'}
    ]

    /**
     * Possible operators.
     *
     * @type {{displayName: string, enumValue: string}[]}
     */
    $scope.operators = [
        {displayName: '=', enumValue: 'EQ'},
        {displayName: '>', enumValue: 'GT'},
        {displayName: '>=', enumValue: 'GTEQ'},
        {displayName: '<', enumValue: 'LT'},
        {displayName: '<=', enumValue: 'LTEQ'},
        {displayName: '!=', enumValue: 'NE'}
    ];

    /**
     * Holds the meetings currently displayed in the page.
     * @type {Array}
     */
    $scope.meetings = [];

    /**
     * Holds the state if offcanvas is enabled.
     *
     * @type {boolean}
     */
    $scope.isOffcanvasEnabled = false;

    /**
     * Sets the selected tab to 'ALL'
     */
    $scope.tabAllSelected = function () {
        $scope.selectedTab = 'ALL';
        $scope.queryMeetings();
    };

    /**
     * Sets the selected tab to 'YOU_HAVE_CREATED'
     */
    $scope.tabYouHaveCreatedSelected = function () {
        $scope.selectedTab = 'YOU_HAVE_CREATED';
        if (!oauth2Provider.signedIn) {
            oauth2Provider.showLoginModal();
            return;
        }
        $scope.queryMeetings();
    };

    /**
     * Sets the selected tab to 'YOU_WILL_ATTEND'
     */
    $scope.tabYouWillAttendSelected = function () {
        $scope.selectedTab = 'YOU_WILL_ATTEND';
        if (!oauth2Provider.signedIn) {
            oauth2Provider.showLoginModal();
            return;
        }
        $scope.queryMeetings();
    };

    /**
     * Toggles the status of the offcanvas.
     */
    $scope.toggleOffcanvas = function () {
        $scope.isOffcanvasEnabled = !$scope.isOffcanvasEnabled;
    };

    /**
     * Namespace for the pagination.
     * @type {{}|*}
     */
    $scope.pagination = $scope.pagination || {};
    $scope.pagination.currentPage = 0;
    $scope.pagination.pageSize = 20;
    /**
     * Returns the number of the pages in the pagination.
     *
     * @returns {number}
     */
    $scope.pagination.numberOfPages = function () {
        return Math.ceil($scope.meetings.length / $scope.pagination.pageSize);
    };

    /**
     * Returns an array including the numbers from 1 to the number of the pages.
     *
     * @returns {Array}
     */
    $scope.pagination.pageArray = function () {
        var pages = [];
        var numberOfPages = $scope.pagination.numberOfPages();
        for (var i = 0; i < numberOfPages; i++) {
            pages.push(i);
        }
        return pages;
    };

    /**
     * Checks if the target element that invokes the click event has the "disabled" class.
     *
     * @param event the click event
     * @returns {boolean} if the target element that has been clicked has the "disabled" class.
     */
    $scope.pagination.isDisabled = function (event) {
        return angular.element(event.target).hasClass('disabled');
    }

    /**
     * Adds a filter and set the default value.
     */
    $scope.addFilter = function () {
        $scope.filters.push({
            field: $scope.filtereableFields[0],
            operator: $scope.operators[0],
            value: ''
        })
    };

    /**
     * Clears all filters.
     */
    $scope.clearFilters = function () {
        $scope.filters = [];
    };

    /**
     * Removes the filter specified by the index from $scope.filters.
     *
     * @param index
     */
    $scope.removeFilter = function (index) {
        if ($scope.filters[index]) {
            $scope.filters.splice(index, 1);
        }
    };

    /**
     * Query the meetings depending on the tab currently selected.
     *
     */
    $scope.queryMeetings = function () {
        $scope.submitted = false;
        if ($scope.selectedTab == 'ALL') {
            $scope.queryMeetingsAll();
        } else if ($scope.selectedTab == 'YOU_HAVE_CREATED') {
            $scope.getMeetingsCreated();
        } else if ($scope.selectedTab == 'YOU_WILL_ATTEND') {
            $scope.getMeetingsAttend();
        }
    };

    /**
     * Invokes the meeting.queryMeetings API.
     */
    $scope.queryMeetingsAll = function () {
        var sendFilters = {
            filters: []
        }
        for (var i = 0; i < $scope.filters.length; i++) {
            var filter = $scope.filters[i];
            if (filter.field && filter.operator && filter.value) {
                sendFilters.filters.push({
                    field: filter.field.enumValue,
                    operator: filter.operator.enumValue,
                    value: filter.value
                });
            }
        }
        $scope.loading = true;
        gapi.client.meeting.queryMeetings(sendFilters).
            execute(function (resp) {
                $scope.$apply(function () {
                    $scope.loading = false;
                    if (resp.error) {
                        // The request has failed.
                        var errorMessage = resp.error.message || '';
                        $scope.messages = 'Failed to query meetings : ' + errorMessage;
                        $scope.alertStatus = 'warning';
                        $log.error($scope.messages + ' filters : ' + JSON.stringify(sendFilters));
                    } else {
                        // The request has succeeded.
                        $scope.submitted = false;
                        $scope.messages = 'Query succeeded : ' + JSON.stringify(sendFilters);
                        $scope.alertStatus = 'success';
                        $log.info($scope.messages);

                        $scope.meetings = [];
                        angular.forEach(resp.items, function (meeting) {
                            $scope.meetings.push(meeting);
                        });
                    }
                    $scope.submitted = true;
                });
            });
    }

    /**
     * Invokes the meeting.getMeetingsCreated method.
     */
    $scope.getMeetingsCreated = function () {
        $scope.loading = true;
        gapi.client.meeting.getMeetingsCreated().
            execute(function (resp) {
                $scope.$apply(function () {
                    $scope.loading = false;
                    if (resp.error) {
                        // The request has failed.
                        var errorMessage = resp.error.message || '';
                        $scope.messages = 'Failed to query the meetings created : ' + errorMessage;
                        $scope.alertStatus = 'warning';
                        $log.error($scope.messages);

                        if (resp.code && resp.code == HTTP_ERRORS.UNAUTHORIZED) {
                            oauth2Provider.showLoginModal();
                            return;
                        }
                    } else {
                        // The request has succeeded.
                        $scope.submitted = false;
                        $scope.messages = 'Query succeeded : Meetings you have created';
                        $scope.alertStatus = 'success';
                        $log.info($scope.messages);

                        $scope.meetings = [];
                        angular.forEach(resp.items, function (meeting) {
                            $scope.meetings.push(meeting);
                        });
                    }
                    $scope.submitted = true;
                });
            });
    };

    /**
     * Retrieves the meetings to attend by calling the meeting.getProfile method and
     * invokes the meeting.getMeeting method n times where n == the number of the meetings to attend.
     */
    $scope.getMeetingsAttend = function () {
        $scope.loading = true;
        gapi.client.meeting.getMeetingsToAttend().
            execute(function (resp) {
                $scope.$apply(function () {
                    if (resp.error) {
                        // The request has failed.
                        var errorMessage = resp.error.message || '';
                        $scope.messages = 'Failed to query the meetings to attend : ' + errorMessage;
                        $scope.alertStatus = 'warning';
                        $log.error($scope.messages);

                        if (resp.code && resp.code == HTTP_ERRORS.UNAUTHORIZED) {
                            oauth2Provider.showLoginModal();
                            return;
                        }
                    } else {
                        // The request has succeeded.
                        $scope.meetings = resp.result.items;
                        $scope.loading = false;
                        $scope.messages = 'Query succeeded : Meetings you will attend (or you have attended)';
                        $scope.alertStatus = 'success';
                        $log.info($scope.messages);
                    }
                    $scope.submitted = true;
                });
            });
    };
});


/**
 * @ngdoc controller
 * @name MeetingDetailCtrl
 *
 * @description
 * A controller used for the meeting detail page.
 */
meetingApp.controllers.controller('MeetingDetailCtrl', function ($scope, $log, $routeParams, HTTP_ERRORS) {
    $scope.meeting = {};

    $scope.isUserAttending = false;

    /**
     * Initializes the meeting detail page.
     * Invokes the meeting.getMeeting method and sets the returned meeting in the $scope.
     *
     */
    $scope.init = function () {
        $scope.loading = true;
        gapi.client.meeting.getMeeting({
            websafeMeetingKey: $routeParams.websafeMeetingKey
        }).execute(function (resp) {
            $scope.$apply(function () {
                $scope.loading = false;
                if (resp.error) {
                    // The request has failed.
                    var errorMessage = resp.error.message || '';
                    $scope.messages = 'Failed to get the meeting : ' + $routeParams.websafeKey
                        + ' ' + errorMessage;
                    $scope.alertStatus = 'warning';
                    $log.error($scope.messages);
                } else {
                    // The request has succeeded.
                    $scope.alertStatus = 'success';
                    $scope.meeting = resp.result;
                }
            });
        });

        $scope.loading = true;
        // If the user is attending the meeting, updates the status message and available function.
        gapi.client.meeting.getProfile().execute(function (resp) {
            $scope.$apply(function () {
                $scope.loading = false;
                if (resp.error) {
                    // Failed to get a user profile.
                } else {
                    var profile = resp.result;
                    for (var i = 0; i < profile.meetingKeysToAttend.length; i++) {
                        if ($routeParams.websafeMeetingKey == profile.meetingKeysToAttend[i]) {
                            // The user is attending the meeting.
                            $scope.alertStatus = 'info';
                            $scope.messages = 'You are attending this meeting';
                            $scope.isUserAttending = true;
                        }
                    }
                }
            });
        });
    };


    /**
     * Invokes the meeting.registerForMeeting method.
     */
    $scope.registerForMeeting = function () {
        $scope.loading = true;
        gapi.client.meeting.registerForMeeting({
            websafeMeetingKey: $routeParams.websafeMeetingKey
        }).execute(function (resp) {
            $scope.$apply(function () {
                $scope.loading = false;
                if (resp.error) {
                    // The request has failed.
                    var errorMessage = resp.error.message || '';
                    $scope.messages = 'Failed to register for the meeting : ' + errorMessage;
                    $scope.alertStatus = 'warning';
                    $log.error($scope.messages);

                    if (resp.code && resp.code == HTTP_ERRORS.UNAUTHORIZED) {
                        oauth2Provider.showLoginModal();
                        return;
                    }
                } else {
                    if (resp.result) {
                        // Register succeeded.
                        $scope.messages = 'Registered for the meeting';
                        $scope.alertStatus = 'success';
                        $scope.isUserAttending = true;
                        $scope.meeting.seatsAvailable = $scope.meeting.seatsAvailable - 1;
                    } else {
                        $scope.messages = 'Failed to register for the meeting';
                        $scope.alertStatus = 'warning';
                    }
                }
            });
        });
    };

    /**
     * Invokes the meeting.unregisterForMeeting method.
     */
    $scope.unregisterFromMeeting = function () {
        $scope.loading = true;
        gapi.client.meeting.unregisterFromMeeting({
            websafeMeetingKey: $routeParams.websafeMeetingKey
        }).execute(function (resp) {
            $scope.$apply(function () {
                $scope.loading = false;
                if (resp.error) {
                    // The request has failed.
                    var errorMessage = resp.error.message || '';
                    $scope.messages = 'Failed to unregister from the meeting : ' + errorMessage;
                    $scope.alertStatus = 'warning';
                    $log.error($scope.messages);
                    if (resp.code && resp.code == HTTP_ERRORS.UNAUTHORIZED) {
                        oauth2Provider.showLoginModal();
                        return;
                    }
                } else {
                    if (resp.result) {
                        // Unregister succeeded.
                        $scope.messages = 'Unregistered from the meeting';
                        $scope.alertStatus = 'success';
                        $scope.meeting.seatsAvailable = $scope.meeting.seatsAvailable + 1;
                        $scope.isUserAttending = false;
                        $log.info($scope.messages);
                    } else {
                        var errorMessage = resp.error.message || '';
                        $scope.messages = 'Failed to unregister from the meeting : ' + $routeParams.websafeKey +
                            ' : ' + errorMessage;
                        $scope.messages = 'Failed to unregister from the meeting';
                        $scope.alertStatus = 'warning';
                        $log.error($scope.messages);
                    }
                }
            });
        });
    };
});


/**
 * @ngdoc controller
 * @name RootCtrl
 *
 * @description
 * The root controller having a scope of the body element and methods used in the application wide
 * such as user authentications.
 *
 */
meetingApp.controllers.controller('RootCtrl', function ($scope, $location, oauth2Provider) {

    /**
     * Returns if the viewLocation is the currently viewed page.
     *
     * @param viewLocation
     * @returns {boolean} true if viewLocation is the currently viewed page. Returns false otherwise.
     */
    $scope.isActive = function (viewLocation) {
        return viewLocation === $location.path();
    };

    /**
     * Returns the OAuth2 signedIn state.
     *
     * @returns {oauth2Provider.signedIn|*} true if siendIn, false otherwise.
     */
    $scope.getSignedInState = function () {
        return oauth2Provider.signedIn;
    };

    /**
     * Calls the OAuth2 authentication method.
     */
    $scope.signIn = function () {
        oauth2Provider.signIn(function () {
            gapi.client.oauth2.userinfo.get().execute(function (resp) {
                $scope.$apply(function () {
                    if (resp.email) {
                        oauth2Provider.signedIn = true;
                        $scope.alertStatus = 'success';
                        $scope.rootMessages = 'Logged in with ' + resp.email;
                    }
                });
            });
        });
    };

    /**
     * Render the signInButton and restore the credential if it's stored in the cookie.
     * (Just calling this to restore the credential from the stored cookie. So hiding the signInButton immediately
     *  after the rendering)
     */
    $scope.initSignInButton = function () {
        gapi.signin.render('signInButton', {
            'callback': function () {
                jQuery('#signInButton button').attr('disabled', 'true').css('cursor', 'default');
                if (gapi.auth.getToken() && gapi.auth.getToken().access_token) {
                    $scope.$apply(function () {
                        oauth2Provider.signedIn = true;
                    });
                }
            },
            'clientid': oauth2Provider.CLIENT_ID,
            'cookiepolicy': 'single_host_origin',
            'scope': oauth2Provider.SCOPES
        });
    };

    /**
     * Logs out the user.
     */
    $scope.signOut = function () {
        oauth2Provider.signOut();
        $scope.alertStatus = 'success';
        $scope.rootMessages = 'Logged out';
    };

    /**
     * Collapses the navbar on mobile devices.
     */
    $scope.collapseNavbar = function () {
        angular.element(document.querySelector('.navbar-collapse')).removeClass('in');
    };

});


/**
 * @ngdoc controller
 * @name OAuth2LoginModalCtrl
 *
 * @description
 * The controller for the modal dialog that is shown when an user needs to login to achive some functions.
 *
 */
meetingApp.controllers.controller('OAuth2LoginModalCtrl',
    function ($scope, $modalInstance, $rootScope, oauth2Provider) {
        $scope.singInViaModal = function () {
            oauth2Provider.signIn(function () {
                gapi.client.oauth2.userinfo.get().execute(function (resp) {
                    $scope.$root.$apply(function () {
                        oauth2Provider.signedIn = true;
                        $scope.$root.alertStatus = 'success';
                        $scope.$root.rootMessages = 'Logged in with ' + resp.email;
                    });

                    $modalInstance.close();
                });
            });
        };
    });

/**
 * @ngdoc controller
 * @name DatepickerCtrl
 *
 * @description
 * A controller that holds properties for a datepicker.
 */
meetingApp.controllers.controller('DatepickerCtrl', function ($scope) {
    $scope.today = function () {
        $scope.dt = new Date();
    };
    $scope.today();

    $scope.clear = function () {
        $scope.dt = null;
    };

    // Disable weekend selection
    $scope.disabled = function (date, mode) {
        return ( mode === 'day' && ( date.getDay() === 0 || date.getDay() === 6 ) );
    };

    $scope.toggleMin = function () {
        $scope.minDate = ( $scope.minDate ) ? null : new Date();
    };
    $scope.toggleMin();

    $scope.open = function ($event) {
        $event.preventDefault();
        $event.stopPropagation();
        $scope.opened = true;
    };

    $scope.dateOptions = {
        'year-format': "'yy'",
        'starting-day': 1
    };

    $scope.formats = ['dd-MMMM-yyyy', 'yyyy/MM/dd', 'shortDate'];
    $scope.format = $scope.formats[0];
});
