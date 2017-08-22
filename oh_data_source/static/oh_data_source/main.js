// jQuery for data selection

$(document).ready(function(){
	
	$(function() {
		
		$('input[name="afterDate"]').daterangepicker({
		    singleDatePicker: true,
		    showDropdowns: true,
			autoUpdateInput: false,
			cancelLabel: 'Clear'
		}, 
		
		function(start, end, label) {
		    
		});
		
	});

	$('input[name="afterDate"]').on('apply.daterangepicker', function(ev, picker) { 
		$(this).val(picker.startDate.format('YYYY-MM-DD')); 
	});

	$('input[name="afterDate"]').on('cancel.daterangepicker', function(ev, picker) {
		$(this).val('');
	});

	$(function() {
		$('input[name="beforeDate"]').daterangepicker({
		    singleDatePicker: true,
		    showDropdowns: true,
			autoUpdateInput: false,
			cancelLabel: 'Clear'
		}, 
		function(start, end, label) {
		    
		});
	});

	$('input[name="beforeDate"]').on('apply.daterangepicker', function(ev, picker) {
		$(this).val(picker.startDate.format('YYYY-MM-DD'));
  	});

	$('input[name="beforeDate"]').on('cancel.daterangepicker', function(ev, picker) {
		$(this).val('');
	});
}); // end of $(document).ready()
