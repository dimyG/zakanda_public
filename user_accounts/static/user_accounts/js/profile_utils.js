/**
 * Created by xene on 8/2/2016.
 */

define([
    'js/utils',
    'js/urls',
    'jquery',
    'js/libs/jquery.pjax'
], function(Utils, Urls, $){
    var config = {
        debug: Utils.config.logger.user_accounts,
        //profile_form_data_attr: "data-pjax_form",  // Not used anymore, the form is submitted with the default pjax form submitting mechanism
        input_switch_name: 'profile_mode',
        // The url_param_class is added to any link that returns both normalized and not normalized data. A url param
        // is added to their href. This is done in order for the responses to be cached separately. This has a meaning
        // on the responses the cached version of which depends on the url. In all others it isn't needed. Not
        // necessary for Profile stats since only the empty template is cached and which version you get depends on the
        // money session value.
        url_param_class: "url_param_dependent",
        currency_url_param: "normalized"
    };

    var log = Utils.create_logger(config.debug);
    var glog = Utils.logger();
    var main_container = Utils.config.main_container;
    //var profile_form_data_attr = config.profile_form_data_attr;
    var stats_mode_url = Urls.user_accounts.stats_mode;

    function confirm_email_removal(){
        var message = "Do you really want to remove the selected e-mail address?";
        var actions = document.getElementsByName('action_remove');
        if (actions.length) {
            actions[0].addEventListener("click", function(e) {
                if (! confirm(message)) {
                    e.preventDefault();
                }
            });
        }
    }

    function add_url_param(param, value){
        //qs = (qs == null) ? new Utils.QS() : qs;
        // I can either create a new qs object any tme I want to add/remove params to it, or create "global" object
        // and add/remove from it. Now I use the first approach
        var qs = new Utils.QS();
        log('qs before adding:', JSON.stringify(qs));
        qs.add(param, value);
        log('qs after adding:', JSON.stringify(qs));
        // pjax doesn't work if you manually affect the state (with pushState or replaceState). As a workaround
        // we use the $.pjax.state
        history.replaceState($.pjax.state, null, "?" + qs.toString());
    }

    function remove_url_param(param){
        //qs = (qs == null) ? new Utils.QS() : qs;
        var qs = new Utils.QS();
        log('qs before removing:', JSON.stringify(qs));
        qs.remove(param);
        log('qs after removing:', JSON.stringify(qs));
        var current_url = window.location.origin + window.location.pathname;
        Object.keys(qs.qs).length == 0 ?
        history.replaceState($.pjax.state, null, current_url) :
        history.replaceState($.pjax.state, null, "?" + qs.toString());
    }

    function add_remove_url_param(state){
        //if true remove normalized url_param
        //if false add normalizd param
        if (state){
            // state = true -> on -> currency option
            remove_url_param(config.currency_url_param)
        }else{
            add_url_param(config.currency_url_param, 'On')
        }
    }

    function update_switch_dependent_hrefs(){
        // it updates the hrefs of the links with a specific class. It adds the normalize url param or
        // removes it depending on the switch state
        var state = $("[name="+config.input_switch_name+"]").bootstrapSwitch('state');
        if (!state) {
            // it's not necessary to use the currency param_url. Just anything that changes the url, so that
            // it is cached differently than the original url that returns the currency data
            $('a.' + config.url_param_class).each(function () {
                var original_href = $(this).attr('href');
                if (original_href.indexOf(config.currency_url_param) < 0) {
                    // the currency_url_param doesn't exist in the current url, so we must add it
                    var new_href = original_href + '?' + config.currency_url_param + '=' + 'On';
                    $(this).attr('href', new_href);
                }
            });
        }else{
            $('a.'+config.url_param_class).each(function(){
                var original_href = $(this).attr('href');
                var new_href = original_href.replace('?' + config.currency_url_param + '=' + 'On', '');
                $(this).attr('href', new_href);
            });
        }
    }

    function init(){
        $("[name="+config.input_switch_name+"]").bootstrapSwitch();
        update_switch_dependent_hrefs();
    }

    function bind_events(){
        //$(document).on('submit', "form["+profile_form_data_attr+"]", function(event) {
        //    event.preventDefault();
        //    custom_pjax_submit($(this), null);
        //});

        $(document).on("switchChange.bootstrapSwitch", "[name="+config.input_switch_name+"]", function(event, state){
            // state is true if switch is On which in my case is the Currency option.
            update_switch_dependent_hrefs();  // have in mind that this in also called from init in order to
            // update he links when a page is loaded (either normally or ajax). But I must have it also here
            // because in some pages the change of the switch doesn't lead to page reload so no init happens
            var current_url = window.location.href;
            $.ajax({
                url: stats_mode_url,
                type: 'GET',
                data: {
                    state: state
                },
                datatype: 'json',
                success: function (data, status, xhr){
                    log('state', state);
                    add_remove_url_param(state);
                    var new_url = window.location.href;
                    reload_page(new_url);
                    //log("success", data, status)
                },
                error: function(data){
                    //log("error", data)
                }
            });
        });

        confirm_email_removal();
    }

    function reload_page(url){
        glog('reloading url:', url);
        // Here are the urls that contain statistics that can be presented either in abs on in norm mode
        var total_bet_list_url_matched = Urls.stats.total_bet_list_regex.exec(url);
        var profile_stats_url_matched = Urls.stats.profile_template_regex.exec(url);
        var tb_detail_url_matched = Urls.stats.total_bet_detail_regex.exec(url);
        var bev_table_template_url_matched = Urls.stats.bet_events_table_template_regex.exec(url);
        var deposits_list_url_matched = Urls.bet_tagging.deposits_list_regex.exec(url);
        var bet_tag_list_url_matched = Urls.bet_tagging.bet_tag_list.exec(url);
        var user_tips_url_matched = Urls.user_accounts.user_tips_regex.exec(url);
        var tips_overview_url_matched = Urls.gutils.tips_overview_regex.exec(url);

        if (tb_detail_url_matched || bev_table_template_url_matched || deposits_list_url_matched
            || bet_tag_list_url_matched || total_bet_list_url_matched || user_tips_url_matched
            || tips_overview_url_matched){
            log('money switch dependend url matched');
            $.pjax.reload(main_container)
        }else if (profile_stats_url_matched){
            //$.pjax.reload(left_and_main_container)
            $.pjax.reload(main_container)
        }
    }

    //function custom_pjax_submit($this, callback){
    //    var form = $this;
    //    // the form created by django has no action tag. The submit is done in the current page
    //    var form_url = form.attr("action");
    //    if (!form_url){form_url = window.location.href}
    //
    //    var type = form.attr("method");
    //    var data = form.serialize();
    //    //log("from data", data);
    //    //log("form url", form_url);
    //    //log("form type", type);
    //
    //    $.pjax({
    //        url:form_url,
    //        type:type,
    //        container: main_container,
    //        data:data
    //    }).done(function() {
    //        // .done fires after pjax:success (which means that the page has been updated)
    //        log('Custom pjax done. Form submitted with pjax (fired after pjax:success)');
    //        if (callback){callback();}
    //    });
    //}

    return {
        bind_events: bind_events,
        init: init,
        update_switch_dependent_hrefs: update_switch_dependent_hrefs
    }

});
