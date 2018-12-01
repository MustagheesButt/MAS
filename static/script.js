$(document).ready(function () {
	$("#count").on("change", function () {
		console.log("change...")
		var n = $(this).val(),
			toRepeat = $(".to-repeat"),
			toRepeatN = $(".to-repeat").length,
			entity = $(this)[0].dataset.entity,
			max = +$(this).attr("max");

		if (n > max) {
			$(this).val(max);
			n = max;
		} else if (n < 1) {
			$(this).val(1);
			n = 1;
		}

		var delta = n - toRepeatN;

		if (delta > 0) {
			for (var i = toRepeatN; i < (toRepeatN + delta); i++) {
				var toAppend = $(toRepeat[0]).clone();
				toAppend.find(".entity-number").html(entity + " " + (i + 1));
				$(".append-to").append(toAppend);
			}
		} else if (delta < 0) {
			for (var i = delta; i < 0; i++) {
				$(".append-to .to-repeat:last").remove();
			}
		}
	});

	/** CELESTIAL BINDER **/
	$("input[data-bindto], select[data-bindto]").on("change", function () {
		$($(this)[0].dataset.bindto).val($(this).val());
	});

	/** LOGIN FUNCTIONS **/
	NN.init({
		client_id: 3,
		scope: "id.username.first_name.last_name.email",

		loginCallback: function (response) {
			var url = new URL(window.location);
			response.next = url.searchParams.get("next");
			
			$.post("/auth", response, function (data) {

				console.log(data);

				if (data.status == "error")
					console.error(data.error);
				else if (data.status == "success")
					window.location = data.redirect_to;
			});
		}
	});

	$("#login-btn").click(function (e) {
		e.preventDefault();
		NN.login();
	});
});