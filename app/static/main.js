// https://stackoverflow.com/questions/11844256/alert-for-unsaved-changes-in-form
var initial_form_data = {};
var check_form_inputs = true;
function update_form(f, obj) {
    let action = $(f).data('form-id') || $(f).attr('action') || 'self';
    if (action == 'skip') obj[action] = {};
    else obj[action] = $(f).serialize();
    return action;
}
function update_all_forms(obj) {
    $('form').each((i, f) => update_form(f, obj));
}
$(function() {
    update_all_forms(initial_form_data);
    $('form').submit(_ => {check_form_inputs = false;});
    $(window).bind('beforeunload', function(e) {
        if (check_form_inputs) {
            let cur = {};
            let mismatch = false;
            $('form').each((i, f) => {
                let a = update_form(f, cur);
                if (a != 'skip' && cur[a] != initial_form_data[a]) {
                    mismatch = true;
                }
            });
            if (mismatch) {
                e.preventDefault();
                return true;
            }
        }
    });
    $(window).bind('htmx:afterSwap', function(e) {
      $(e.target).find('form').each((i, f) => update_form(f, initial_form_data));
      $(e.target).find('.filter-select').select2();
    });
    $('.filter-select').select2();
});
