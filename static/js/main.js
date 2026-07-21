var pathname = window.location.pathname;

function cargarTooltip(){
	$(function () {
		  $('[data-toggle="tooltip"]').tooltip()
		})
}

function showMessage(tag, text){
	Swal.fire({
		"title": tag,
		"text": text,
		"icon": tag,
		"showConfirmButton": false,
		"timer": 1700                
	})
}

function showMessagent(tag, text){
	Swal.fire({
		"title": tag,
		"text": text,
		"icon": tag,
		"showConfirmButton": true		              
	})
}

function back(url){
	window.location.replace(url);   
}

function checkProfile(id_select){
	var user_profile = $(id_select+' option:selected').val();
	if(user_profile == 'contributor'){		
		$('#country').prop('disabled', 'disabled');
	}
	else{
		$("#country").removeAttr("disabled");
	}
}


$(document).ready(function(){
	AOS.init();
});

