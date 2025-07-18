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
  });
  $(window).bind('htmx:afterSettle', function(e) {
    // afterSwap is sometimes too soon to apply select2
    $('.filter-select').select2();
  });
  $('.filter-select').select2();
  $(window).on('animationend', function(e) {
    if (e.target.className == 'status') {
      e.target.style.display = 'none';
    }
  });
});

var alt_state_contents = `<select id="id_mailing-state" name="mailing-state">
	    <option value="AL">Alabama</option>
	    <option value="AK">Alaska</option>
	    <option value="AZ">Arizona</option>
	    <option value="AR">Arkansas</option>
	    <option value="CA">California</option>
	    <option value="CO">Colorado</option>
	    <option value="CT">Connecticut</option>
	    <option value="DE">Delaware</option>
	    <option value="DC">District Of Columbia</option>
	    <option value="FL">Florida</option>
	    <option value="GA">Georgia</option>
	    <option value="HI">Hawaii</option>
	    <option value="ID">Idaho</option>
	    <option value="IL">Illinois</option>
	    <option value="IN">Indiana</option>
	    <option value="IA">Iowa</option>
	    <option value="KS">Kansas</option>
	    <option value="KY">Kentucky</option>
	    <option value="LA">Louisiana</option>
	    <option value="ME">Maine</option>
	    <option value="MD">Maryland</option>
	    <option value="MA">Massachusetts</option>
	    <option value="MI">Michigan</option>
	    <option value="MN">Minnesota</option>
	    <option value="MS">Mississippi</option>
	    <option value="MO">Missouri</option>
	    <option value="MT">Montana</option>
	    <option value="NE">Nebraska</option>
	    <option value="NV">Nevada</option>
	    <option value="NH">New Hampshire</option>
	    <option value="NJ">New Jersey</option>
	    <option value="NM">New Mexico</option>
	    <option value="NY">New York</option>
	    <option value="NC">North Carolina</option>
	    <option value="ND">North Dakota</option>
	    <option value="OH">Ohio</option>
	    <option value="OK">Oklahoma</option>
	    <option value="OR">Oregon</option>
	    <option value="PA">Pennsylvania</option>
	    <option value="RI">Rhode Island</option>
	    <option value="SC">South Carolina</option>
	    <option value="SD">South Dakota</option>
	    <option value="TN">Tennessee</option>
	    <option value="TX">Texas</option>
	    <option value="UT">Utah</option>
	    <option value="VT">Vermont</option>
	    <option value="VA">Virginia</option>
	    <option value="WA">Washington</option>
	    <option value="WV">West Virginia</option>
	    <option value="WI">Wisconsin</option>
	    <option value="WY">Wyoming</option>
    </select>`;
var alt_state_value = '';
function swap_state_input() {
  let val = $('#id_mailing-state').val();
  let html = document.getElementById('id_mailing-state').outerHTML;
  $('#id_mailing-state').replaceWith($(alt_state_contents));
  $('#id_mailing-state').val(alt_state_value);
  alt_state_contents = html;
  alt_state_value = val;
}
function check_state_swap() {
  let is_us = ($('#id_mailing-country').val() == '189');
  let is_select = ($('select#id_mailing-state').length > 0);
  if (is_us != is_select) {
    swap_state_input();
  }
}
$(function() {
  $(window).bind('htmx:afterSwap', function(e) {
    $(e.target).find('#id_mailing-country').bind('change', check_state_swap);
    check_state_swap();
  });
});
