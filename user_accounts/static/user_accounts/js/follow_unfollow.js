/**
 * Created by xene on 6/29/2016.
 */


define([
    'jquery',
    'js/utils'
], function($, Utils) {

    var config = {
        debug: Utils.config.logger.user_accounts,
        // debug: true,
        // actstream app's urls for follow/unfollow is in the form: /activity/follow/4/15/ /activity/unfollow/4/15/
        // follow_button_id: "follow_unfollow",
        follow_button_class: "follow_unfollow",
        href_follow_text: "follow",
        href_unfollow_text: "unfollow",
        follow_style: 'btn_zak_blue_01',
        unfollow_style: 'btn_zak_danger'
    };

    var log = Utils.create_logger(config.debug);
    // var $follow_button_id = '#'+config.follow_button_id;
    var follow_in_url = config.href_follow_text;
    var unfollow_in_url = config.href_unfollow_text;
    // var laddas = {};

    function bind_events() {
        $(document).on("click", 'button.'+config.follow_button_class, function (event) {
            event.preventDefault();
            // $(this).get(0) is the underlying javascript object
            Utils.toggle_ladda_spin(null, $(this).get(0));
            var follow_link = $(this).closest('div').find('a');
            log('link', follow_link, 'button', $(this));
            ajax_follow_unfollow($(this), follow_link);
        });
    }

    function ajax_follow_unfollow($button, $link){
        var href = $link.attr("href");
        log("href: " + href);
        if (Utils.misc_data.user_id === null){
            var message = "Please Login first!";
            $.bootstrapGrowl(message, {type: 'danger', align: 'center'});
            Utils.toggle_ladda_spin(null, $button.get(0));
            return
        }
        $.ajax({
            url: href,
            type: 'GET',
            datatype: 'html',

            success: function (data, status, xhr) {
                if (xhr.status === 201){
                    log("follow object created");
                    var unfollow_href = href.replace(follow_in_url, unfollow_in_url); // change href to "unfollow"
                    $link.attr("href", unfollow_href);
                    // Notice: a new ladda instance will be created each time. To avoid this you must keep a list
                    // of all the instances and pass the correct one (based on button id) to the function instead of null
                    Utils.toggle_ladda_spin(null, $button.get(0));
                    $button.find('span.ladda-label').html("UnFollow");
                    $button.removeClass(config.follow_style).addClass(config.unfollow_style);
                    //    todo update sidebar number
                }else if (xhr.status === 204){
                    log("follow object deleted");
                    var follow_href = href.replace(unfollow_in_url, follow_in_url); // change href to "follow"
                    $link.attr("href", follow_href);
                    Utils.toggle_ladda_spin(null, $button.get(0));
                    $button.find('span.ladda-label').html("Follow");
                    $button.removeClass(config.unfollow_style).addClass(config.follow_style);
                    //    todo update sidebar number
                }else{
                    Utils.toggle_ladda_spin(null, $button.get(0));
                    log("unsupported response type", xhr.status);
                    // log(data);
                }
            },
            error: function(data) {
                Utils.toggle_ladda_spin(null, $button.get(0));
                var message = 'AJAX Error. Please reload the page and try again!';
                log(data, message);
                $.bootstrapGrowl(message, {type: 'danger', align: 'center'});
            }
        });
    }

    return{
        bind_events: bind_events,
        config: config
    }

});