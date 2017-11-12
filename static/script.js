$(document).ready(function () {
	$("#count").on("change", function () {
		console.log("change...")
		var n = $(this).val(),
			toRepeat = $(".to-repeat"),
			toRepeatN = $(".to-repeat").length,
			entity = $(this)[0].dataset.entity;

		if (n > 20) {
			$(this).val(20);
			n = 20;
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
});