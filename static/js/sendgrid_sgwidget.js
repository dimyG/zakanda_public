define(['jquery', 'js/utils', 'bootstrap_growl'], function($, Utils) {

    var submit_btn = document.getElementById("btn-newsletter");
    var form = document.getElementById("form-newsletter");
    var subscribe_btn_ladda = null;

    function bind_events(){
        if (!submit_btn || !form){
            return
        }
        submit_btn.addEventListener("click", function (e) {
            subscribe_btn_ladda = Utils.toggle_ladda_spin(null, submit_btn);

            var email = '';

            if (document.getElementById('mail-newsletter')) {
                email = stripHTML(document.getElementById('mail-newsletter').value);
            } else {
                email = stripHTML(document.getElementById('email').value);
            }

            if (!email || !isValidEmailAddress(email)) {
                var message = 'Please enter a valid email address';
                $.bootstrapGrowl(message, {type: 'danger', align: 'center'});
                Utils.toggle_ladda_spin(subscribe_btn_ladda);
                document.getElementById('mail-newsletter').value = '';
                return;
            }
            submitFormAjax();

        }, false);
    }

    function submitFormAjax() {
        var url = 'https://sgwidget.leaderapps.co/v2/api/newsletter-signup';
        //var url = 'https://sgwidget.test/v2/api/newsletter-signup';

        var email = '';
        var first_name = '';
        var last_name = '';


        if (document.getElementById('mail-newsletter')) {
            email = stripHTML(document.getElementById('mail-newsletter').value);
        } else {
            email = stripHTML(document.getElementById('email').value);
        }

        if (document.getElementById('sg_signup_first_name')) {
            first_name = stripHTML(document.getElementById('sg_signup_first_name').value);
        }
        if (document.getElementById('sg_signup_last_name')) {
            last_name = stripHTML(document.getElementById('sg_signup_last_name').value);
        }

        var data = new FormData();
        data.append('email', email);
        data.append('first_name', first_name);
        data.append('last_name', last_name);
        data.append('token', form.dataset.token);
        // console.log('data', email, first_name, last_name);
        var xmlhttp = window.XMLHttpRequest ?
            new XMLHttpRequest() : new ActiveXObject("Microsoft.XMLHTTP");

        xmlhttp.open("POST", url, true);
        xmlhttp.onload = function () {
            var resp = JSON.parse(xmlhttp.responseText);
            if (xmlhttp.status == 200) {
                if (resp.message.indexOf('error') !== -1) {
                    $.bootstrapGrowl(resp.message, {type: 'danger', align: 'center'});
                    Utils.toggle_ladda_spin(subscribe_btn_ladda);
                    document.getElementById('mail-newsletter').value = '';
                } else {
                    $.bootstrapGrowl(resp.message, {type: 'success', align: 'center'});
                    Utils.toggle_ladda_spin(subscribe_btn_ladda);
                    document.getElementById('mail-newsletter').value = '';
                }
            } else if (xmlhttp.status == 500) {
                // if you are already subscribed a 500 error code is returned. So I modified the
                // message to tell that. Notice that if there is a real error the same message will be shown
                $.bootstrapGrowl(resp.message, {type: 'danger', align: 'center'});
                Utils.toggle_ladda_spin(subscribe_btn_ladda);
                document.getElementById('mail-newsletter').value = '';
            }
        };
        xmlhttp.send(data);
    }

    function stripHTML(text) {
        var regex = /(<([^>]+)>)/ig;
        return text.replace(regex, "");
    }

    function isValidEmailAddress(emailAddress) {
        var pattern = /^([a-z\d!#$%&'*+\-\/=?^_`{|}~\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]+(\.[a-z\d!#$%&'*+\-\/=?^_`{|}~\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]+)*|"((([ \t]*\r\n)?[ \t]+)?([\x01-\x08\x0b\x0c\x0e-\x1f\x7f\x21\x23-\x5b\x5d-\x7e\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]|\\[\x01-\x09\x0b\x0c\x0d-\x7f\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]))*(([ \t]*\r\n)?[ \t]+)?")@(([a-z\d\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]|[a-z\d\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF][a-z\d\-._~\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]*[a-z\d\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])\.)+([a-z\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]|[a-z\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF][a-z\d\-._~\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]*[a-z\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])\.?$/i;
        return pattern.test(emailAddress);
    }

    return{
        bind_events: bind_events
    }
});