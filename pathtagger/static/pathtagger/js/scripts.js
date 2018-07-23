function toggle_all_checkboxes(source, checkbox_name) {
    var checkboxes = document.getElementsByName(checkbox_name);
    for (var i = 0, n = checkboxes.length; i<n; i++) {
        checkboxes[i].checked = source.checked;
    }
}

function enable_all_radio_action_type(commonAncestorId, actionType) {
    var ancestor = document.getElementById(commonAncestorId);
    var inputs = ancestor.getElementsByTagName('input');
    for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].type == 'radio' && inputs[i].name.startsWith('tag_') && inputs[i].value == actionType) {
            inputs[i].checked = true;
        }
    }
}
