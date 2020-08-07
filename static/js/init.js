/**
 * Created by xene on 4/6/2016.
 */

define([
    'js/router',
    'js/utils',
    'bet_slip/js/bet_slip',
    'games/js/bookmakers_list',
    'bet_statistics/js/total_bets_charts',
    'bet_statistics/js/bet_events_charts',
    'bet_statistics/js/datatables_setup',
    'user_accounts/js/follow_unfollow',
    'feeds/js/stream_client',
    'user_accounts/js/profile_utils',
    'bet_tagging/js/bet_tagging',
    'bet_statistics/js/filters',
    'django_comments_xtd/js/comments_utils',
    'jquery',
    'metronic_app',
    'layout',
    'demo',
    'quick_sidebar',
    'quick_nav',
    'js/sendgrid_sgwidget',
    'slimscroll',
    'js/libs/jquery.pjax',
    'js/google_analytics_amd'
], function(Router, Utils, Bet_slip, Booker_list, Total_bet_charts, Bet_event_charts, Datatables_setup, Follow_unfollow, Stream_client,
            Profile_utils, Bet_tagging, Filters, Comment_utils, $, Metronic_app, Layout, Demo, Quick_sidebar,
            Quick_nav, Sendgrid_sgwidget){

    var config = {
        debug: Utils.config.logger.init,
        // debug: true,
        //todo HIGH change pjax timeout
        pjax_timeout: 12000
    };

    var log = Utils.create_logger(config.debug);
    var glog = Utils.logger();
    var main_container = Utils.config.main_container;
    var left_sidebar_container = Utils.config.left_sidebar_container;
    var left_and_main_container = Utils.config.left_and_main_container;
    var pjax_timeout = config.pjax_timeout;

    // todo to del
    function clear_db_handler(){
        $(document).on('click', 'li.delete_all', function(){
        //$('li.delete_all').on('click', function(){
            var clear_db = confirm('Are you sure you want to Empty the Database?');
            if (!clear_db){
                $(this).find('a').attr('href', window.location.pathname);
            }
        });
    }

    function bind_datatables_in_tabs_events(){
        var datatables = Utils.datatables;
        $(document).on('shown.bs.tab', 'a[data-toggle="tab"]', function (e) {
            // The width of a responsive datatable must be explicitly calculated if the table was initialy hidden
            // When you use responsive datatables inside tabs, the datatable of inactive tabs are hidden.
            // So their width must be explicitly recalculated. This event handler is attached to all tabs
            var tab_id = $(e.target).attr("href"); // activated tab
            var table_id = $(tab_id+'.tab-pane').find('table').attr('id');
            table_id = '#' + table_id;
            if (datatables && datatables[table_id]){
                datatables[table_id].columns.adjust();
                datatables[table_id].responsive.recalc();
            }
        });
    }

    function generic_events(){
        // Not currently in use
        $(window).on("popstate", function(){
            log(" >>> POPSTATE...");
            var current_href = window.location.href;
            Router.back_forward(current_href);
        });
        $(window).bind("pageshow", function(event){
            // After the creation of AMD modules and require.js pageshow doesn't work as before.
            // Now I trigger the refresh router by the document.ready

            // The pageshow event fires when a session history entry is being traversed to. This includes back/forward
            // as well as initial page-showing after the onload event.
            // the pageshow fires after the load event fires the first time the page loads. Then it fires also on back/for buttons
            // But there is an Error: Every time the pageshow event fires (no matter if its the first time or from back button)
            // the persisted variable is False. It should be true in the second case. So the if here never fires. Only the else.
            log(" >>> PAGESHOW...");
            var current_href = window.location.href;
            if (event.originalEvent.persisted == true){
                log("event.originalEvent.persisted", event.originalEvent.persisted);
                log("back to page");
                log("this page was hard loaded (A session history entry has been traversed to)");
                //Bet_slip.serve_initial_bet_form();
                //Booker_list.update_bookmaker_name_in_session();
            }
            else{
                //log("document pageshow event fired, serve_initial_bet_form is to be called..");
                log("event.originalEvent.persisted", event.originalEvent.persisted);
                log("(the page was normally hard loaded from the server) -or- (the page was loaded from browser's cache and the previous page was fully loaded)");
                //log("first time in page");
                //log("current href ", current_href);
                //Router.refresh(current_href);
            }
        });

        // $(window).on('resize', function (e) {
        //
        // });

        $(document).on("loadstart", function(){
            log(" >>> LOADSTART...");
        });

        $(document).on('submit', 'form[data-pjax]', function(event) {
            // any form that needs to be submitted with pjax must have a data-pjax attribute and a
            // data-pjax_container too. The 2nd one is the container that the response will replace.
            // It must much the container ids defined in utils.js
            var container_id = $(this).data('pjax_container');
            $.pjax.submit(event, container_id)
        });

        bind_datatables_in_tabs_events();

        $(document).on('rendered_with_json', function(){
            Profile_utils.update_switch_dependent_hrefs();
        });

        clear_db_handler();
    }

    function on_pjax_start(event, xhr, options){
        // In back/forward no xhr object is send to the server. Content is loaded from the cache
        log(" >>> PJAX START...");
        if (! xhr){
            //var current_href = window.location.href;
            //log("current href: "+ current_href);
            //Router.pjax_start_from_cache(current_href)
        }
        else{
            //var target_url = options.url;
            //log("target url: " + target_url);
            //Router.pjax_start_normal(target_url)
        }
        //log('options: ', options);
        log(" >>> pjax started done");
    }

    function on_pjax_beforeReplace(contents, options){
        log(" >>> PJAX BEFORE REPLACE...");
        //log('contents: ', contents);
        //log('options: ', options);
        log(" >>> before replace done");
    }

    function on_pjax_success(data, status, xhr, options){
        log(" >>> PJAX SUCCESS...");
        //log('xhr: ', xhr);
        //log('options: ', options);
        log(' >>> pjax success done');
    }

    function on_pjax_popstate(){
        // on pjax:popstate pjax.js makes a pjax call to the url. So this call doesn't appear in my code
        log(" >>> PJAX POPSTATE...");
        log("(back/forward action, without traversing to a session history entry, previous page was loaded with pjax)");
        log(" >>> pjax popstate done")
    }

    function on_pjax_end(pjax_state, event, xhr, options){
        log(" >>> PJAX END...");
        if (! xhr){
            // Page has been loaded from the browser's cache
            // (for all modern browsers that support pjax which means that support pushState)
            //log("(Page was loaded from the browser's cache)");
            var current_href = window.location.href;
            //log("current href ", current_href);

            //update_bookmaker_name_in_session();
            Router.from_cache(current_href);
        }
        else{
            log("xhr: ", xhr);
            var target_url = options.url;
            if (pjax_state.error){
                // if there is a pjax:error the window.location.href is the url that you were before pressing the pjax link
                //log("(page wasn't partially updated, a hard refresh will follow)");
                Router.pjax_fail(target_url);
            }else{
                //log("(part of page was updated with data from server)");
                Router.main_pjax(target_url);
            }
        }
        pjax_state.error = false;
        log(" >>> pjax end done \n");
    }

    function on_pjax_error(pjax_state, xhr, textStatus, errorThrown, options){
        log(' >>> PJAX ERROR...');
        pjax_state.error = true;
        log('xhr: ', xhr);
        log('xhr.responseText: ', xhr.responseText, 'textStatus: ', textStatus, 'errorThrown: ', errorThrown);
        log('options: ', options);
        log(' >>> pjax error done');
    }

    function on_pjax_complete(event, xhr, textStatus, options){
        log(' >>> PJAX COMPLETE...');
        //log('xhr: ', xhr);
        //log('textStatus: ', textStatus);
        //log('options: ', options);
        $('#main_loader').addClass('hidden');
        log(' >>> pjax complete done');
    }

    function on_pjax_send(event, xhr, textStatus, options){
        log(' >>> PJAX SEND...');
        $('#main_loader').removeClass('hidden');
        log(' >>> pjax send done');
    }

    function generic_pjax_events(){
        // only pjax.error and pjax.end are being used. They are used for routing
        var pjax_state = {};
        pjax_state.error = false;

        // Important: The left_and_main_container contains the main_container and the left_sidebar_container divs.
        // So, even if only the left_sidebar or main container is updated with pjax, the event is delegated to its parent
        // div and it is caught.
        // You can catch events from left_sidebar or main, by attaching event handlers for these containers and
        // then to Stop the event propagation. This way if the left is updated the left handler is executed first
        // and after its execution it stops its propagation, so the left_and_main (its parent) will not fire.
        // Currently I use the same handlers for all of them, but I can differentiate the treatment of each event.
        $(document).on("pjax:start", left_and_main_container, function(event, xhr, options){
            on_pjax_start(event, xhr, options)
        });

        $(document).on("pjax:beforeReplace", left_and_main_container, function(event, contents, options){
            on_pjax_beforeReplace(contents, options)
        });

        $(document).on("pjax:send", left_and_main_container, function(event, xhr, textStatus, options){
            on_pjax_send(event, xhr, textStatus, options);
        });

        $(document).on("pjax:success", left_and_main_container, function(event, data, status, xhr, options){
            on_pjax_success(data, status, xhr, options)
        });

        $(document).on("pjax:popstate", left_and_main_container, function(event){
            on_pjax_popstate()
        });

        $(document).on("pjax:end", left_and_main_container, function(event, xhr, options){
            on_pjax_end(pjax_state, event, xhr, options);
        });

        $(document).on('pjax:error', left_and_main_container, function(event, xhr, textStatus, errorThrown, options){
            on_pjax_error(pjax_state, xhr, textStatus, errorThrown, options)
        });

        $(document).on('pjax:complete', left_and_main_container, function(event, xhr, textStatus, options){
            on_pjax_complete(event, xhr, textStatus, options)
        });



        $(document).on("pjax:start", left_sidebar_container, function(event, xhr, options){
            on_pjax_start(event, xhr, options);
            event.stopPropagation();
        });

        $(document).on("pjax:beforeReplace", left_sidebar_container, function(event, contents, options){
            on_pjax_beforeReplace(contents, options);
            event.stopPropagation();
        });

        $(document).on("pjax:send", left_sidebar_container, function(event, xhr, textStatus, options){
            // no loader is shown for the left sidebar loading
            //on_pjax_send(event, xhr, textStatus, options);
            event.stopPropagation();
        });

        $(document).on("pjax:success", left_sidebar_container, function(event, data, status, xhr, options){
            on_pjax_success(data, status, xhr, options);
            event.stopPropagation();
        });

        $(document).on("pjax:popstate", left_sidebar_container, function(event){
            on_pjax_popstate();
            event.stopPropagation();
        });

        $(document).on("pjax:end", left_sidebar_container, function(event, xhr, options){
            on_pjax_end(pjax_state, event, xhr, options);
            event.stopPropagation();
        });

        $(document).on('pjax:error', left_sidebar_container, function(event, xhr, textStatus, errorThrown, options){
            on_pjax_error(pjax_state, xhr, textStatus, errorThrown, options);
            event.stopPropagation();
        });

        $(document).on('pjax:complete', left_sidebar_container, function(event, xhr, textStatus, options){
            on_pjax_complete(event, xhr, textStatus, options);
            event.stopPropagation();
        });
    }

    function module_specific_events(){
        Utils.bind_events();
        Profile_utils.bind_events();
        Booker_list.bind_events();
        Bet_slip.bind_events();
        Total_bet_charts.bind_events();
        Bet_event_charts.bind_events();
        Follow_unfollow.bind_events();
        Stream_client.bind_events();
        Bet_tagging.bind_events();
        Filters.bind_events();
        Comment_utils.bind_events();
        Sendgrid_sgwidget.bind_events();
    }

    function module_specific_pjax_events(){
        Booker_list.bind_pjax_events();
    }

    function bind_events(){
        //$(document).on('click', '#init', function(){
        //    Layout.initSidebarAjax();
        //});
        generic_events();
        module_specific_events();
    }

    function bind_pjax_events(){
        generic_pjax_events();
        module_specific_pjax_events();
    }

    function metronic_init(){
        // Metronic theme related initializations
        log('>>> Metronic initialization...');
        Metronic_app.init();
        if (Metronic_app.isAngularJsApp() === false) {
            //jQuery(document).ready(function() {
                Layout.init();
                Demo.init();
                Quick_sidebar.init();
            //});
        }
        Quick_nav.init();
    }

    function init(){
        Router.init();  // Router initialization runs also on ajax loaded pages (pjax)
        metronic_init();
    }

    var test = {};
    test.t1 = function(){
        var a = [];
        a[3] = 4;
        a[4] = 5;
        a[100] = 11;
        log('TEST:', a.length, a[a.length-1]);
        var b = [];
        log(b.length)
    };
    test.t2 = function(){
        //var regex = new RegExp(location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+'/Stats/Profile/'+'d+/g');
        var regex = new RegExp("http://zakanda:8000/Stats/(\\d+)/");
        var url = "http://zakanda:8000/Stats/124/";
        var s = url.search(regex);
        var m = url.match(regex);
        var t = regex.test(url);
        var e = regex.exec(url);
        log("s: " + s + " m: " + m + " t: "+ t + " e: " + e[1]);

        var left_sidebar_class = 'sports_list';
        var res = $(Utils.config.left_sidebar_container).find('div.'+left_sidebar_class);
        if (res){
            log('found: ' + res[0]);
        }else{
            log('not found');
        }

        var user_info_regex = new RegExp(location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+"/LeftSidebar/UserInfo/");
        var user_info_url = "http://http://192.168.50.0:8000/LeftSidebar/UserInfo/1/";
        var user_info_left_sidebar_url = user_info_regex.exec(user_info_url);
        log("REGEX", user_info_left_sidebar_url)
    };
    test.t3 = function(){
        var s1 = '?bookmaker=';
        var s2 = '?bookmaker=bet365';
        var match1 = s1.match(/([?|&]bookmaker=)/);
        var match2 = s2.match(/([?|&]bookmaker=)[^\&]+/);
        console.warn("match1", match1);
        console.warn("match2", match2);
    };

    test.t4 = function () {
        console.log('running test 4...');
        var url = 'https://www.zakanda.com/api/v1.0/odds/';
        $.ajax({
            type: 'GET',
            headers: {
                'zakanda-api-key':'your-key'
            },
            url: url,
            datatype: 'json',
            data: {
                // optional parameters
                num_days: 1,  // you will get data for the events within 1 day from now, default=3
                num_events: 4  // you will get data for 4 events only, default=250
            },
            success: function (json_data) {
                console.log(json_data);
            },
            error: function (json_data) {
                console.log("Ajax error:", json_data.responseText);
            }
        })
    };

    function initialize(){
        glog("initializing...");
        Utils.get_misc_server_data();  // so the data exist when the document is ready
        $(document).ready(function(){
            glog(" >>> DOCUMENT READY...");
            // test.t4();
            init();
            bind_events();
            if ($.support.pjax){
                //$.pjax.disable();
                // pjax works in browsers that support the history.pushState API
                $(document).pjax('a.pjax_call', main_container);
                $(document).pjax('a.pjax_call_timeout45', main_container, {"timeout": 45000});
                $(document).pjax('a.pjax_call_left_main', left_and_main_container); // not used anymore
                $.pjax.defaults.timeout = pjax_timeout;
                $.pjax.defaults.maxCacheLength = 0;
                bind_pjax_events();
            }else{
                log("pjax is not supported by your browser");
            }
            var current_href = window.location.href;
            Router.refresh(current_href);
        });
    }

    return {
        initialize: initialize
    }

});

