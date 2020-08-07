/**
 * Created by xene on 4/8/2016.
 */

// There are 3(+2) cases for a page:
//
// 1) normal full page load from server ---> document.ready, pageshow
//
// 2) partial server load with pjax ---> pjax:end
//
// 3) back/forward cached page. The previous page was loaded with pjax. ---> pjax:popstate, pjax:end xhr=null, popstate
//    pageshow doesn't fire so there is no session history state traversing
//    Notice that the pjax:popstate fires even if the target page wasn't loaded with pjax.
//
// 4) The 4th case is not actually a new case. Its just a full page load. But it happens on B/F when the previous page was a full page load
//    and the target page was partially loaded with pjax. If the target page was fully loaded and the previous page was fully loaded
//    then B/F brings the page from the cache.
//
// 5) pjax failure (for example due to timeout) ---> I keep the fact that pjax:error occurred in a variable and use it in pjax:end

// The pjax:popstate fires on back/forward, pjax starts and ends but without sending an xhr object (it doesn't make an ajax call)
// This is the test I do to determine if its a cached page.
// In the back/forward buttons, in which the page loads from the browser's cache, pjax:popstate fires and pjax starts but without sending
// an xhr object (without making an ajax request). It just starts, the before_replace event fires and ends. The before_replace fires just
// before the page is replaced from the one in the cache. So you can interact with the cached page afterwards, after the
// pjax end event fires. In the cached page case, the xhr object of start and end events is null since there is no
// ajax request to the server. (The options argument is the ajax options of the ajax request (status, response, etc) that
// pjax does). So: In case the xhr object is null then the page has been loaded from the cache.
//
// On back/forward button: Either the document.ready event will fire or the pjax:postate depending on if the previous page was
// fully loaded from server or if it was partially loaded with pjax


define([
    'js/utils',
    'js/urls',
    'bet_slip/js/bet_slip',
    'games/js/bookmakers_list',
    'bet_statistics/js/profile_stats',
    'feeds/js/stream_client',
    //'bet_statistics/js/leaderboard',
    'bet_statistics/js/datatables_setup',
    'bet_statistics/js/filters',
    // 'user_accounts/js/follow_unfollow',
    'user_accounts/js/profile_utils',
    'bet_tagging/js/bet_tagging',
    'dc',
    'layout',
    'jasny_bootstrap',
    'jquery',
    // 'django_comments_xtd/js/plugin-amd-2.0.8',
    'js/dyn_modules'
    // 'js/libs/ajaxcomments',
    // 'django_ajax_comments_xtd/js/ajax_comments_amd'
], function(Utils, Urls, Bet_slip, Booker_list, Profile_stats, Stream_client, /* Leaderboard,*/ Datatables_setup,
            Filters, Profile_utils, Bet_tagging, dc, Layout, Jasny, $, dynModules){

    var config = {
        debug: Utils.config.logger.router,
        // debug: true,
        urls: Urls
    };

    var log = Utils.create_logger(config.debug);
    var glog = Utils.logger();
    var urls = config.urls;
    var main_container = Utils.config.main_container;
    var left_sidebar_container = Utils.config.left_sidebar_container;
    var sports_list_class = Utils.config.sports_list_class;
    var user_info_class = Utils.config.user_info_class;

    function dynamically_load_comments_plugin(){
        // it loads the return value of the dynModules dynamically. This was done since the comments xtd plugin
        // code is loaded and executed immediately and it needs to find a comments element
        // console.log("Dynamically loading modules...");
        requirejs.undef('js/dyn_modules');
        requirejs.undef('django_comments_xtd/js/plugin-amd-2.0.8');
        requirejs.undef('django_comments_xtd/js/vendor-amd-2.0.8');
        require(dynModules, function(){
            // use arguments since you don't know how many modules you're getting in the callback
            // for (var i = 0; i < arguments.length; i++){
                // var mymodule = arguments[i];
                // do something with mymodule...
            // }
        });
    }

    function global_init(){
        $('[data-toggle="tooltip"]').tooltip();
        $('.fileinput').fileinput();  // added to jquery from jasny_bootstrap
    }

    function initialization(){
        // The initialization must be done here since this function is called on every "event" (pjax, normal, from cache)
        // and not only on document.ready.
        log(">>> Page Initialization...");
        global_init();
        Utils.init();
        Filters.init();
        Booker_list.init();
        Datatables_setup.init();
        Profile_utils.init();
        Profile_stats.init();
        Bet_tagging.init();
        // Comments_ajax.watch();
    }

    function custom_pjax_call(url){
        log("custom pjax call...");
        // todo pjax fail (timeout or other) I must manually load the main container since the
        // left sidebar call will be a normal load. To do this I need to keep the url that the user was. You
        // can do this by joining the left_sidebar urls with the existing url instead of having distinct left sidebar urls
        var type = "GET";
        $.pjax({
            url:url,
            type:type,
            container:left_sidebar_container,
            push: false,
            replace: false,
            timeout: 20000,
            maxCacheLength: 0  // not caching this seems to solve the problem of back on full page load. The target page
                                 // is still requested with the wrong container
        }).done(function(data){
            log("left sidebar was updated!");
            Layout.initSidebarAjax();
        });
    }

    function update_left_sidebar(left_sidebar_class, user_id){
        log("  updating left sidebar...");
        // each different left sidebar must have a div (the parent div) with a unique class name that acts as
        // an identifier for the type of left sidebar.
        // the given argument is this class. The argument dictates the type of left sidebar that we want to have.
        // we check if the given class exists in the left sidebar. If it exists then the left sidebar is the one
        // that is supposed to be. If it isn't then we reload the corresponding left sidebar using pjax
        log('  sidebar must be of class: %s', left_sidebar_class);
        var $left_wrapper = $(left_sidebar_container).find('div.'+left_sidebar_class);
        log('  existing sidebar class is: %s', $(left_sidebar_container + ' > div').attr('class'));
        //console.log('  the requested class was found in the existing sidebar: %s', $left_wrapper[0]);
        if ($left_wrapper[0] === undefined){
            log("  left sidebar is of the wrong type...");
            if (left_sidebar_class == sports_list_class){
                log('[INFO] UPDATING LEFT SIDEBAR WITH %s CLASS', left_sidebar_class);
                custom_pjax_call(urls.left_sidebar.sports_list)
            }else if(left_sidebar_class == user_info_class) {
                // this is currently not used
                log('[INFO] UPDATING LEFT SIDEBAR WITH %s CLASS', left_sidebar_class);
                custom_pjax_call(urls.left_sidebar.user_info + user_id + "/")
            }else{
                log("  [WARNING] UNKNOWN LEFT SIDEBAR CLASS REQUESTED")
            }
        }else{
            log("  left sidebar is of the correct type...");
            //    if the existing sidebar class is the same with the one that we want it to be
            //    then we check the data-user_id attribute to see if the user_info left sidebar
            //    is for the user that we want it to be
            if(left_sidebar_class == user_info_class) {
                log("  checking if it matches the correct user...");
                var existing_sidebar_user_id = $left_wrapper.data("user_id");
                if (existing_sidebar_user_id != user_id){
                    log('  not matching the correct user');
                    log('[INFO] UPDATING LEFT SIDEBAR WITH %s CLASS AND USER ID %s', left_sidebar_class, user_id);
                    custom_pjax_call(urls.left_sidebar.user_info + user_id + "/")
                }
            }
        }
    }

    function left_sidebar_type_handling(url){
        log('handling left sidebar type (with url %s)...', url);

        while (1){
            // Here are all the urls for which we want the user dependent content to match the left sidebar user
            // So if you see the profile stats or the bet groups of a user then the left sidebar must correspond
            // to this user. All these urls must contain the user_id in the url. We get this id from the url and
            // we update the left sidebar accordingly.
            // The loop breaks on the first matched regex
            var matched_user_pk = null;

            var profile_stats_url = urls.stats.profile_template_regex.exec(url);
            if (profile_stats_url != null){matched_user_pk = profile_stats_url[1]; break;}

            var relations_url = urls.user_accounts.users_relation_list_regex.exec(url);
            if (relations_url != null){matched_user_pk = relations_url[1]; break;}

            var tbs_url = urls.stats.total_bet_list_regex.exec(url);
            if (tbs_url != null){matched_user_pk = tbs_url[1]; break;}

            var bevs_url = urls.stats.bet_events_table_template_regex.exec(url);
            if (bevs_url != null){matched_user_pk = bevs_url[1]; break;}

            var tips_url = urls.user_accounts.user_tips_regex.exec(url);
            if (tips_url != null){matched_user_pk = tips_url[1]; break;}

            var bet_tags_url = urls.bet_tagging.bet_tag_list.exec(url);
            if (bet_tags_url != null){matched_user_pk = bet_tags_url[1]; break;}

            var left_sidebar_url = urls.left_sidebar.left_sidebar_regex.exec(url);
            var bet_picking_url = urls.games.bets_picking_regex.exec(url);

            if (!matched_user_pk){break;}
        }
        if (matched_user_pk){
             log('left sidebar must match with user id %s', matched_user_pk);
        }

        //var left_sidebar_links = [profile_stats_url, relations_url, tbs_url, bevs_url, tips_url, bet_tags_url];
        //var left_sidebar_link_idx = left_sidebar_links.indexOf(true);
        //console.log('left_sidebar_link_idx', left_sidebar_link_idx);

        var logged_user_id = Utils.misc_data.user_id;
        log('  logged user id: %s', logged_user_id);

        if (left_sidebar_url){
            // if the left sidebar has just been updated then no further actions required
            log('left sidebar was just updated with custom pjax, no further actions required!');
            return
        }

        if(!logged_user_id){
            if(matched_user_pk){
                update_left_sidebar(user_info_class, matched_user_pk);
            }else{
                update_left_sidebar(sports_list_class, logged_user_id);
            }
        }else{
            if(bet_picking_url){
                update_left_sidebar(sports_list_class, logged_user_id);
            }else if(matched_user_pk){
                update_left_sidebar(user_info_class, matched_user_pk);
            }else{
                update_left_sidebar(user_info_class, logged_user_id);
            }
        }
    }

    function back_forward(url){
        log("-back/forward operation on page %s -", url);
        if (url.indexOf('normalized') >= 0) {
            // url param back issue. You are on bets with normal On. The url has the url param On. You visit
            // a tb_detail link. You change the switch to currency. Url param dissapears. You press back. The history
            // entry contains the url param On and so you see the browser cached normalized data while the switch
            // is on Currency. So in this case I programmatically change the switch value to false (off). 3rd
            // argument: if the switch event will be blocked or not. With false it fires and corresponding actions are
            // executed.
            // With this solution the switch changes and the page is loaded again instead of showing the cached one.
            $("[name=profile_mode]").bootstrapSwitch('state', false, false);
        }
    }

    function from_cache(url){
        // NOTICE: If the pjax cache time setting is set to 0 then this routing never works
        glog("-page %s loaded from browser's cache-", url);
        pre_treatment_common(url);

        Booker_list.update_bookmaker_name_in_session(Bet_slip.get_bet_slip);  // is this necessary?

        var profile_stats_url = urls.stats.profile_template_regex.exec(url);

        if (profile_stats_url) {
            // we must get the profile data because otherwise the javascript doesn't work and there is no interactivity
            var matched_user_pk = profile_stats_url[1];
            Profile_stats.get_profile_data(matched_user_pk);

            // we must update the left sidebar
            // The Case: main_and_left is updated. The left is user info. Then the main is updated and the left
            // is updated individually.
            // If you press back, then only the main gets loaded from cache and is the correct one. The left remains
            // as it is. So we need to update it. We do it in the from_cache routing. But then, when the loading ends,
            // it triggers a main_pjax routing. So in the main pjax routing we check if the url that was loaded
            // is the left sidebar. If it is then we must not load it with sports_list_class.
            if ($.support.pjax) {update_left_sidebar(user_info_class, matched_user_pk);}
        }else{
            if ($.support.pjax){update_left_sidebar(sports_list_class, null);}
        }
        initialization();
    }

    function is_url_with_comment(url){
        for (var i=0; i<Urls.comment_urls.length; i++){
            if (Urls.comment_urls[i].exec(url)){
                return true
            }
        }
        return false
    }

    function refresh(url){
        glog("-- url " + url + " loaded with full refresh --");
        pre_treatment_common(url);

        Stream_client.listen_to_stream();
        Bet_slip.serve_initial_bet_form();
        Booker_list.update_bookmaker_name_in_session(Bet_slip.get_bet_slip);  // is this necessary?
        // if the page doesn't contain the bookmaker list, the update_bookmaker will not call it's callback(get_bet_slip),
        // so we need to call it again. So in case that the page does contain it, the call will be done twice
        Bet_slip.get_bet_slip();

        var profile_stats_url = urls.stats.profile_template_regex.exec(url);
        var bevs_table_template_url = urls.stats.bet_events_table_template_regex.exec(url);

        left_sidebar_type_handling(url);

        if (profile_stats_url){
            // in order for the pk to be returned by exec() the (\d+) of the regex must be inside parentheses
            var matched_user_pk = profile_stats_url[1];
            Profile_stats.get_profile_data(matched_user_pk);
        //}else if(url == urls.stats.leader_board_template){
        //    Leaderboard.get_leaderboard_data();
        }else if(bevs_table_template_url) {
            var matched_user_id = bevs_table_template_url[1];
            Datatables_setup.get_data(matched_user_id);
        }else{
            // update the sidebar only if pjax is supported. This is done in order to avoid blank main container if the
            // browser doesn't support pjax
            //if ($.support.pjax){update_left_sidebar(sports_list_class, null);}
        }
        if (is_url_with_comment(url)){
            dynamically_load_comments_plugin();
        }
        initialization();
    }

    function main_pjax(url){
        glog("-- a part of the page loaded with pjax, by calling the " + url + " url --");
        pre_treatment_common(url);

        var profile_stats_url = urls.stats.profile_template_regex.exec(url);
        var user_info_left_sidebar = urls.left_sidebar.user_info_regex.exec(url);
        var users_relation_list = urls.user_accounts.users_relation_list_regex.exec(url);
        var bevs_table_template_url = urls.stats.bet_events_table_template_regex.exec(url);
        var left_sidebar_url = urls.left_sidebar.left_sidebar_regex.exec(url);

        left_sidebar_type_handling(url);

        if (!left_sidebar_url){
            // Trigger a custom event that will be used to stop the long polling of the comments_xtd plugin
            // The event is caught in the commentbox.jsx file of the plugin.

            // the comments_xtd plugin js implements a long polling for new comments using a set_interval function
            // the js is loaded only in pages with comments. In single page apps the code continues to run even
            // if you visit another page. So you need to manually stop it if you visit another page. If its
            // a left sidebar page update then you are still in the same page so no need to stop the polling.

            // (In hard reload there is no need to manually stop it since the script is not loaded
            // from pages without comments)
            $(document).trigger('main_pjax_excluding_sidebar');
        }
        if (profile_stats_url){
            var matched_user_pk = profile_stats_url[1];
            Profile_stats.get_profile_data(matched_user_pk);
        }else if(user_info_left_sidebar || users_relation_list){
            // for these urls I don't want to update the left sidebar
            // see from_cache comment
        //}else if(url == urls.stats.leader_board_template){
        //    Leaderboard.get_leaderboard_data();
        }else if(bevs_table_template_url) {
            var matched_user_id = bevs_table_template_url[1];
            Datatables_setup.get_data(matched_user_id);
        }else{
            //if ($.support.pjax){update_left_sidebar(sports_list_class, null);}
        }
        if (is_url_with_comment(url)){
            dynamically_load_comments_plugin()
        }
        initialization();
    }

    function pjax_fail(url){
        initialization();
        glog("-pjax call to %s url failed-", url);
    }

    function pre_treatment_common(url){
        // Any actions that must take place no matter if the page loaded with pjax or not,
        // are placed here. It runs before the load method specific actions.
        // Any load method specific actions must be in their respective functions
        // (from_cache(), refresh(), main_pjax()).

        var profile_stats_url = urls.stats.profile_template_regex.exec(url);

        if (profile_stats_url){
            // currently such elements are only in this url so no need to run it for all urls
            Utils.update_screen_size_related_elements();
        }
        // if (url === urls.bet_tagging.withdraw_create){
            // Bet_tagging.update_withdraw_limits();
        // }
    }

    return{
        back_forward: back_forward,
        from_cache: from_cache,
        refresh: refresh,
        main_pjax: main_pjax,
        pjax_fail: pjax_fail,
        init: initialization
    }

});


