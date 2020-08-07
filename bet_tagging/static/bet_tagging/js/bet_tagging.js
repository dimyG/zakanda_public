/**
 * Created by xene on 8/25/2016.
 */

define([
    'js/utils',
    'js/urls'
], function(Utils, Urls) {

    var config = {
        bet_tags_modal_id: "#bet_tags_modal",
        ok_button_id: '#bet_tags_select_ok',
        checkboxes_name: 'available_bet_tag',
        url_wrapper: '#bet_description_url_wrapper',

        deposit_form_id: "#create_deposit",
        withdraw_form_id: "#create_withdrawal",
        forms_amount_id: "#id_amount",  // the default django form id
        del_bet_tag_class: "delete_bet_tag",
        deposit_create_url: Urls.bet_tagging.deposit_create,
        premium_en: 'Premium',

        balance_id: "#total_balance_number",
        balance_url: Urls.bet_tagging.balance
    };

    var bet_tags_modal_id = config.bet_tags_modal_id;
    var ok_button_id = config.ok_button_id;
    var checkboxes_name = config.checkboxes_name;
    var total_balance = null;

    function confirm_delete(e){
        return confirm('Are you sure you want to delete this Bet Group? Your bets will be added to your default Bet Group');
    }

    function selected_bet_tags(){
        var selected_tag_ids = [];
        var selected_tag_names = [];
        var selected_tag_balances = [];
        var $checked_options = $('input[name='+checkboxes_name+']:checked');
        $checked_options.each(function(){
            if($(this).is(":checked")){
                selected_tag_ids.push($(this).data('id'));
                selected_tag_names.push($(this).data('name'));
                selected_tag_balances.push($(this).data('balance'));
            }
        });
        // log("selected_tag_ids", selected_tag_ids);
        return {
            selected_tag_ids: selected_tag_ids,
            selected_tag_names: selected_tag_names,
            selected_tag_balances: selected_tag_balances
        }
    }

    function handle_service_forms_visibility(bet_group_type){
        // console.debug('selected bet group type: ' + bet_group_type);
        if (bet_group_type === config.premium_en){
            // even if the page and the select text are translated the select values are not. They are always in english
            $('#service_forms').removeClass('hidden')
        }else{
            $('#service_forms').addClass('hidden')
        }
    }

    function to_json(variable){
        if (variable == null){
            variable = JSON.stringify("");
        }else{
            variable = JSON.stringify(variable);
        }
        return variable
    }

    function get_bet_description(){
        var bet_description = $("#bet_description").val();
        var jsoned_bet_description = to_json(bet_description);
        return jsoned_bet_description
    }

    function get_bet_description_url_obj(){
        var bet_description_url = $("#bet_description_url_wrapper").find('input').val();
        //console.log("bet_description_url: ", bet_description_url);
        var is_valid_url = true;
        if(bet_description_url != null){  // if the input elem is found (bet details called)
            if (bet_description_url.trim().length != 0){  // if it is not empty
                is_valid_url = validate_url(bet_description_url);
        }}
        var jsoned_bet_description_url = to_json(bet_description_url);
        //console.log("url obj: ", {"url": jsoned_bet_description_url, "is_valid": is_valid_url});
        return {"url": jsoned_bet_description_url, "is_valid": is_valid_url}
    }

    function validate_url(text) {
        //var urlregex = /^(https?|ftp):\/\/([a-zA-Z0-9.-]+(:[a-zA-Z0-9.&%$-]+)*@)*((25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]?)(\.(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])){3}|([a-zA-Z0-9-]+\.)*[a-zA-Z0-9-]+\.(com|edu|gov|int|mil|net|org|biz|arpa|info|name|pro|aero|coop|museum|[a-zA-Z]{2}))(:[0-9]+)*(\/($|[a-zA-Z0-9.,?'\\+&%$#=~_-]+))*$/;
        var url_regex = /((([A-Za-z]{3,9}:(?:\/\/)?)(?:[\-;:&=\+\$,\w]+@)?[A-Za-z0-9\.\-]+|(?:www\.|[\-;:&=\+\$,\w]+@)[A-Za-z0-9\.\-]+)((?:\/[\+~%\/\.\w\-_]*)?\??(?:[\-\+=&;%@\.\w_]*)#?(?:[\.\!\/\\\w]*))?)/;
        return url_regex.test(text);
    }

    function reload_balance(){
        $.ajax({
            type: 'GET',
            url: config.balance_url,
            data: '',
            success: function(value){
                //console.log('reload', data);
                var balance_id = config.balance_id;
                var balance_number = $(balance_id);
                balance_number.html(value.toFixed(1));
                total_balance = value;
            },
            error: function(data){
                var message = "Error on AJAX";
                if(data.responseText.indexOf('Error') > -1){
                    message = "Balance wasn't reloaded. Reload the page if you want to see the new balance!"
                }
                //glog(data, message);
                //$.bootstrapGrowl(message, {type: 'danger', align: 'center'});
            }
        })
    }

    function delayed_balance_reload(delay){
        setTimeout(function() {
            // delayed execution just to be sure that the balance in server has been updated
            reload_balance();
        }, delay);
    }

    function bet_tag_balance_check(){

    }

    function update_ui_bet_tag(bet_tag_name){
        $('span.active_bet_tag').text(bet_tag_name);
    }

    function update_withdraw_limits(){
        // todo get the limits from the option field and update the max value of the input
        // it must be done whenever the selected option changes too.
        // var form = $('form#create_withdrawal');
        // form.find('input#id_amount').attr('max', 10);
    }

    function initialize () {
        var bet_group_type = $('.bet_group_form #id_type').val();
        handle_service_forms_visibility(bet_group_type);
    }

    function bind_events(){
        $(document).on("change", ".bet_group_form #id_type", function(){
            var bet_group_type = $(this).val();
            handle_service_forms_visibility(bet_group_type);
        });

        $(document).on("click", '.payment_btn', function(){
            var js_btn_object = $(this)[0];
            // var button = document.getElementById('payment_btn');
            var payment_btn_ladda = Utils.toggle_ladda_spin(null, js_btn_object);
            var link = $(this).find('a span');
            link.trigger('click');
        });

        $(document).on("change", "input[type='url']", function(){
            var url_obj = get_bet_description_url_obj();
            var url_wrapper = config.url_wrapper;
            if (!url_obj['is_valid']){
                $(url_wrapper).addClass("has-error");
                $(url_wrapper).find("label").text("Url is not valid!");
            }else{
                $(url_wrapper).removeClass("has-error");
                $(url_wrapper).find("label").text("");
            }
        });

        $(document).on("show.bs.modal", bet_tags_modal_id, function(e) {
            var link = $(e.relatedTarget);
            $(this).find(".modal-body").load(link.attr("href"));
        });

        $(document).on("click", ok_button_id, function(){
            var session_bet_tag = Utils.config.session.bet_tag;

            var selected_bet_tag_id = selected_bet_tags()['selected_tag_ids'][0];
            var selected_bet_tag_name = selected_bet_tags()['selected_tag_names'][0];
            update_ui_bet_tag(selected_bet_tag_name);

            var pair = {};
            pair[session_bet_tag] = selected_bet_tag_id;
            var session_pairs = [pair];
            Utils.update_session(session_pairs);

            $(bet_tags_modal_id).modal('toggle'); // close the modal window
        });

        $(document).on("click", ".toggle_body", function(){
            $(this).parent().find('.panel-body').toggle();
        });

        $(document).on('bet_submitted', function(event){
            //console.log("bet submitted, amount:", bet_amount);
            reload_balance();
        });

        $(document).on('submit', config.deposit_form_id, function(event){
            delayed_balance_reload(1000)
        });

        $(document).on('submit', config.withdraw_form_id, function(event){
            delayed_balance_reload(1000);
        });

        //$(document).on("click", delete_button_id, function(e){
        //    confirm_delete(e);
        //});

        $(document).on("click", 'a.' + config.del_bet_tag_class, function(e){
            var confirm = confirm_delete(e);
            if (confirm){$(this).find('form.' + config.del_bet_tag_class).submit();}
        });

        $(document).on('submit', 'form.' + config.del_bet_tag_class, function(event){
            delayed_balance_reload(1000)
        });
    }

    return {
        bind_events: bind_events,
        init: initialize,
        selected_bet_tags: selected_bet_tags,
        get_bet_description: get_bet_description,
        get_bet_description_url_obj: get_bet_description_url_obj,
        update_withdraw_limits: update_withdraw_limits
    }
});