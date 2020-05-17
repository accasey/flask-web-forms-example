$(function() {
    $(".filter-form").submit(function(e) {
        e.preventDefault();
        let form = $(this);

        if (history.pushState) {
            window.history.replaceState("", "", "/?" + form.serialize());
        }

        $.ajax({
            type: form.attr("method"),
            url: form.attr("action"),
            data: form.serialize() + "&ajax=1"
        }).done(function(data) {
            $(".card-wrapper").empty().append($(data).hide().fadeIn(500));
        });
    });
});