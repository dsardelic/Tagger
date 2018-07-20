function toggle_all_checkboxes(source, checkbox_name) {
    var checkboxes = document.getElementsByName(checkbox_name);
    for (var i = 0, n = checkboxes.length; i<n; i++) {
        checkboxes[i].checked = source.checked;
    }
}
