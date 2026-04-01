var tablename;
var elemId;
var totalNum;
var currentPage=1;
var sortSelected=['','','selected'];
var isSort = false;
var isIncremented = false;

/**
 * Base URL helper (keeps admin UI on same-origin so it works in any environment).
 * If you must override, set window.ADMIN_API_BASE before loading this script.
 */
var API_BASE = (window.ADMIN_API_BASE || (window.location.origin + "/api/"));

$('body').on('focus',".datepicker_recurring_start", function(){
    $(this).datetimepicker({    defaultDate: new Date(),
    format: 'YYYY-MM-DD HH:mm:ss', sideBySide: true});
});

// PUBLIC_INTERFACE
function loadDashboard() {
	/** Load dashboard KPIs + charts using session-protected admin page. */
	setActiveButton("dashboard");
	$("#pageHeader").html("Dashboard");

	$.getJSON(API_BASE + "dashboard/kpis", function(payload){
		if (!payload || !payload.kpis) { return; }
		$("#kpiParcelsToday").text(payload.kpis.parcels_today);
		$("#kpiDriversToday").text(payload.kpis.drivers_connected_today);
		$("#kpiCompletedPercent").text(payload.kpis.completed_percent + "%");
		$("#kpiCompletedBar").css("width", payload.kpis.completed_percent + "%").attr("aria-valuenow", payload.kpis.completed_percent);

		if (payload.work_share) {
			initWorkShareChart(payload.work_share);
		}
	});

	$.getJSON(API_BASE + "money", function(result){
		initMoneyBarChart(result || []);
	});
}

function newPage(data, l1, l2) {
		currentPage=1;
		isSort = false;
		getData(data,l1,l2);
}

function getData (data, l1, l2) {
	if (!isSort)
	{
		tablename = data;
		setActiveButton(data);
		$.getJSON(API_BASE + data, function(result){
	    	totalNum = result.length;
	    	$.getJSON(API_BASE + data + "?limit1="+l1+"&limit2="+l2, function(result){
	    		makeTable(result, l1, l2);
	    	});
	    });
	}
	else
	{
		buildLink(l1,l2);
	}
}

function getHeaders(result){
	var headers = [];
    	$.each(result, function(key, value){
    		headers.push(key);
    	});
    return headers;
}

function makeTable(result, l1, l2){
	isIncremented = false;
	var modalIndex = 0;
	$('#pageHeader').html(tablename.charAt(0).toUpperCase()+tablename.slice(1));
	$('#pageContent').css("margin-right","15px");
   
    table = '<div style="margin-left:5px;" class="row"><div class="col-xl-3 col-md-6 mb-4"><div class="card card-hover border-left-primary shadow h-10 py-2" data-toggle="modal" data-target="#addModal" style="cursor: pointer;"><div class="card-body"><div class="row no-gutters align-items-center"><div class="col mr-2"><div class="text-xs font-weight-bold text-primary text-uppercase mb-1">Add</div><div class="h5 mb-0 font-weight-bold text-gray-800">Create Record</div></div><div class="col-auto"><i class="fas fa-plus fa-2x text-gray-300"></i></div></div></div></div></div>';

    table += '<div class="col-xl-3 col-md-6 mb-4"><div class="card border-left-success shadow h-10 py-2"><div class="card-body"><div class="row no-gutters align-items-center"><div class="col mr-2"><div class="text-xs font-weight-bold text-success text-uppercase mb-1">Number of '+tablename+'</div><div class="h5 mb-0 font-weight-bold text-gray-800">'+totalNum+'</div></div><div class="col-auto"><i class="fas fa-warehouse fa-2x text-gray-300"></i></div></div></div></div></div>';

    if (tablename=='jobs')
    {
    	table+= '<div class="col-xl-3 col-md-6 mb-4"><div class="card border-left-info shadow h-10 py-2" style="height:103px;"><div class="card-body"><div class="row no-gutters align-items-center"><div class="col mr-2"><div class="text-xs font-weight-bold text-info text-uppercase mb-1">Sort Table</div><div class="h5 mb-0 font-weight-bold text-gray-800"><div class="form-group"><select id="selectSortOption" class="form-control" data-role="select-dropdown" data-profile="minimal" onchange="newPageSort(10,0);"><option '+sortSelected[0]+'value="pending">Pending</option><option '+sortSelected[1]+' value="delivered">Delivered</option><option '+sortSelected[2]+' value="all">All</option></select></div></div></div><div class="col-auto" style="top:-14px;"><i class="fas fa-sort fa-2x text-gray-300"></i></div></div></div></div></div>';
    }
    table += '</div>'; 
    table += '<p style="margin-left:18px;">The table does not show all the values in a record. Click on a record to see them all and perform updates. Jobs also support assignment + lifecycle updates.</p>';

	table += '<div style="width:auto;margin:18px;" class="card border-left-warning shadow"><table class="table table-hover"><thead><tr>';
	var headers = getHeaders(result[0]);
	var modals = makeModals(result);
	var picModals = '';

    var i=0;
	for (var header in headers) {
		if (i<8){
			table += '<th scope="col">' + headers[header] + '</th>';
			i++;
		}
	}
	table += '</tr></thead><tbody>';

		var picId = 1;
    	$.each(result, function (key, value) {
    		table += '<tr>';
    		i=0;
    		for (var index in value) {
        		if (i<8){
        			var t = '' + value[index];
        			if (t.toLowerCase().includes('.jpg') || t.toLowerCase().includes('.png') || t.toLowerCase().includes('.gif'))
        			{
        				table += '<td><a style="margin-left:5px;height:30px;cursor:pointer;" data-toggle="modal" data-target="#modalPic'+picId+'" class="text-primary"><i class="fas fa-camera"></i> View picture</a></td>';

        				picModals += '<div class="modal fade" id="modalPic'+picId+'" tabindex="-1" role="dialog" aria-labelledby="myModalLabel"><div class="modal-dialog" role="document"><div class="modal-content"><div class="modal-header"><h4 class="modal-title" id="myModalLabel">Picture</h4><button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button></div><div class="modal-body"><a href="'+value[index]+'" target="_blank"><img style="display:block;width:90%;margin:auto;" src="'+value[index]+'" /></a></div><div class="modal-footer"><button type="button" class="btn btn-dark" data-dismiss="modal">Close</button></div></div></div></div>';
        				picId++;
        			}
        			else
        			{
        				table += '<td data-toggle="modal" data-target="#modal'+modalIndex+'" style="cursor: pointer;">' + value[index] + '</td>';
        			}
        			
        			i++;
         	}
    		}
    		table += '</tr>';
			modalIndex++;
    	});

    table += '</tbody></table></div>';
	table = table.replace(/null/g,'');
	var totalPages = Math.ceil(totalNum/10);
	if (l2==0)
	{
		if (result.length<10)
		{
			table += '<footer><div><div><h3 style="cursor:default;" class="d-inline"><span class="badge badge-secondary"><i class="fas fa-angle-left"></i></span></h3>';
			table += '&nbsp;<h3 style="cursor:default;" class="d-inline"><span class="badge badge-secondary"><i class="fas fa-angle-right"></i></span></h3><div style="width:150px;">Page '+currentPage+' of '+totalPages+'</div></div></div></footer>';
		}
		else
		{
			table += '<footer><div><div><h3 style="cursor:default;" class="d-inline"><span class="badge badge-secondary"><i class="fas fa-angle-left"></i></span></h3>';
			l2+=10;
			table += '&nbsp;<h3 class="d-inline" onclick="getData(\''+tablename+'\','+l1+','+l2+');changePageNum(true);"><span class="badge badge-primary"><i class="fas fa-angle-right"></i></span></h3><div style="width:150px;">Page '+currentPage+' of '+totalPages+'</div></div></div></footer>';
		}
	}
	else
	{
		if (result.length<10)
		{
			l2-=10;
			table += '<footer><div><div><h3 class="d-inline" onclick="getData(\''+tablename+'\','+l1+','+l2+');changePageNum(false);"><span class="badge badge-primary"><i class="fas fa-angle-left"></i></span></h3>';
			table += '&nbsp;<h3 style="cursor:default;" class="d-inline"><span class="badge badge-secondary"><i class="fas fa-angle-right"></i></span></h3><div style="width:150px;">Page '+currentPage+' of '+totalPages+'</div></div></div></footer>';
		}
		else
		{
			l2-=10;
			table += '<footer><div><div><h3 class="d-inline" onclick="getData(\''+tablename+'\','+l1+','+l2+');changePageNum(false);"><span class="badge badge-primary"><i class="fas fa-angle-left"></i></span></h3>';
			l2+=20;
			table += '&nbsp;<h3 class="d-inline" onclick="getData(\''+tablename+'\','+l1+','+l2+');changePageNum(true);"><span class="badge badge-primary"><i class="fas fa-angle-right"></i></span></h3><div style="width:150px;">Page '+currentPage+' of '+totalPages+'</div></div></div></footer>';
		}
	}

    $("#pageContent").html(table);
	$("#modals").html(modals + picModals);
}

/**
 * Build select options for assignment dropdowns.
 */
function buildSelectOptions(items, idKey, labelFn) {
	var html = "<option value=\"None\">Unassigned</option>";
	for (var i=0; i<items.length; i++) {
		var it = items[i];
		var id = it[idKey];
		var label = labelFn(it);
		html += "<option value=\"" + id + "\">" + label + " (#" + id + ")</option>";
	}
	return html;
}

function makeModals(result){
	var modal = '';
	var modalIndex = 0;
	var elemId;

	// Jobs-only: preload drivers/vehicles for assignment dropdowns.
	var driversCache = null;
	var vehiclesCache = null;

	function ensureAssignCaches(cb) {
		if (tablename !== 'jobs') { cb(); return; }
		var pending = 2;

		if (driversCache && vehiclesCache) { cb(); return; }

		$.getJSON(API_BASE + "drivers", function(d){
			driversCache = d || [];
			pending--;
			if (pending === 0) { cb(); }
		});

		$.getJSON(API_BASE + "vehicles", function(v){
			vehiclesCache = v || [];
			pending--;
			if (pending === 0) { cb(); }
		});
	}

	ensureAssignCaches(function() {
		$.each(result, function (key, value) {
	    	modal += '<div class="modal fade" id="modal' + modalIndex + '" tabindex="-1" role="dialog" aria-hidden="true">';
			modal += '<div class="modal-dialog modal-xl" role="document">';
			modal += '<div class="modal-content">';
			modal += '<div class="modal-header">';
			modal += '<h5 class="modal-title">Update Record</h5>';
			modal += '<button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>';
			modal += '</div>';
			modal += '<div class="modal-body"><form name="form'+modalIndex+'">';

			var oddCheck = 0;
			first_iteration = true;

			var currentDriverId = null;
			var currentVehicleId = null;
			var currentStatus = null;

	    	for (var index in value) {
				if (first_iteration){
					elemId=value[index];
					first_iteration=false;
					modal+='<input type="hidden" id="elemId'+modalIndex+'" value="'+elemId+'">';
				}
				else
				{
					if (tablename === 'jobs') {
						if (index === 'DriverID') { currentDriverId = value[index]; }
						if (index === 'VehicleID') { currentVehicleId = value[index]; }
						if (index === 'Status') { currentStatus = value[index]; }
					}

					var disabled = '';
					if (index.toLowerCase().includes('datecreated') || index.toLowerCase().includes('lastconnected'))
					{
							disabled = 'disabled="disabled"';
					}

					if (oddCheck%2==1)
					{
						if (index.toLowerCase().includes('date') || index.toLowerCase().includes('lastconnected'))
						{
							modal +=  '<div class="row"><div class="col-sm"><label>' + index + '</label></div><div class="col-sm"><div id="date" class="input-group date"><input type="text" '+disabled+' class="form-control datepicker_recurring_start" name="' +  index + '" value="' + value[index]+' "/><div class="input-group-append"><span class="input-group-text" id="basic-addon2"><i class="fas fa-calendar-alt"></i></span></div></div></div>';
						}
						else
						{
							modal +=  '<div class="row"><div class="col-sm"><label>' + index + '</label></div><div class="col-sm"><input class="form-control" type="text" name="' +  index + '" value="' + value[index] + '" /></div>';
						}
					}
					else
					{
						if (index.toLowerCase().includes('date') || index.toLowerCase().includes('lastconnected'))
						{
							modal +=  '<div class="col-sm"><label>' + index + '</label></div><div class="col-sm"><div id="date" class="input-group"><input type="text" '+disabled+' class="form-control datepicker_recurring_start" name="' +  index + '" value="' + value[index]+' "/><div class="input-group-append"><span class="input-group-text" id="basic-addon2"><i class="fas fa-calendar-alt"></i></span></div></div></div></div><br>';
						}
						else
						{
	        				modal +=  '<div class="col-sm"><label>' + index + '</label></div><div class="col-sm"><input class="form-control" type="text" name="' +  index + '" value="' + value[index] + '" /></div></div><br>';
						}
					}
				}
				oddCheck++;
	    	}
	    	oddCheck--;
	    	if(oddCheck%2!=0)
	    	{
	    		modal+= '<div class="col-sm"></div><div class="col-sm"></div></div>';
	    	}

	    	if (tablename === 'jobs') {
	    		var driverOpts = buildSelectOptions(driversCache || [], "DriverID", function(d){ return (d.FirstName || "Driver") + (d.LastName ? (" " + d.LastName) : ""); });
	    		var vehicleOpts = buildSelectOptions(vehiclesCache || [], "VehicleID", function(v){ return (v.Make || "Vehicle") + (v.Model ? (" " + v.Model) : "") + (v.Registration ? (" - " + v.Registration) : ""); });

	    		if (currentDriverId && currentDriverId !== "null") {
	    			driverOpts = driverOpts.replace('value="' + currentDriverId + '"', 'value="' + currentDriverId + '" selected');
	    		}
	    		if (currentVehicleId && currentVehicleId !== "null") {
	    			vehicleOpts = vehicleOpts.replace('value="' + currentVehicleId + '"', 'value="' + currentVehicleId + '" selected');
	    		}

	    		modal += '<hr><h6 class="text-primary font-weight-bold">Assignment</h6>';
	    		modal += '<div class="row"><div class="col-sm"><label>Driver</label></div><div class="col-sm"><select id="assignDriver'+modalIndex+'" class="form-control">' + driverOpts + '</select></div>';
	    		modal += '<div class="col-sm"><label>Vehicle</label></div><div class="col-sm"><select id="assignVehicle'+modalIndex+'" class="form-control">' + vehicleOpts + '</select></div></div><br>';
	    		modal += '<button type="button" class="btn btn-info" onclick="assignJob('+elemId+','+modalIndex+');"><i class="fas fa-user-check"></i> Apply Assignment</button>';

	    		modal += '<hr><h6 class="text-primary font-weight-bold">Lifecycle</h6>';
	    		modal += '<div class="btn-group" role="group" aria-label="Job status">';
	    		modal += '<button type="button" class="btn btn-outline-secondary" onclick="setJobStatus('+elemId+',\'Pending\');">Pending</button>';
	    		modal += '<button type="button" class="btn btn-outline-secondary" onclick="setJobStatus('+elemId+',\'Assigned\');">Assigned</button>';
	    		modal += '<button type="button" class="btn btn-outline-secondary" onclick="setJobStatus('+elemId+',\'PickedUp\');">Picked Up</button>';
	    		modal += '<button type="button" class="btn btn-outline-secondary" onclick="setJobStatus('+elemId+',\'InTransit\');">In Transit</button>';
	    		modal += '<button type="button" class="btn btn-outline-success" onclick="setJobStatus('+elemId+',\'Delivered\');">Delivered</button>';
	    		modal += '<button type="button" class="btn btn-outline-danger" onclick="setJobStatus('+elemId+',\'Cancelled\');">Cancelled</button>';
	    		modal += '</div>';
	    		if (currentStatus) {
	    			modal += '<p class="mt-2 mb-0"><small>Current status: <b>' + currentStatus + '</b></small></p>';
	    		}
	    	}
	    	
			modal += '</form></div><div class="modal-footer"><button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button><button type="button" class="btn btn-danger" data-toggle="modal" onclick="getRowId(\\'elemId'+modalIndex+'\\');" data-target="#deleteModal" data-dismiss="modal">Delete</button><button type="button" class="btn btn-primary" data-dismiss="modal" onclick="updateRecord('+modalIndex+','+elemId+',\\''+tablename+'\\');">Save changes</button></div></div></div></div>';
			modalIndex++;
	    });
	});

	var headers = getHeaders(result[0]);
	
	modal += '<div class="modal fade" id="addModal" tabindex="-1" role="dialog" aria-hidden="true"><div class="modal-dialog modal-xl" role="document"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Create Record</h5><button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button></div><div class="modal-body"><form name="createForm" id="createForm">';

	var first_iteration = true;
	oddCheck = 0;
	for (var header in headers) {
		if (first_iteration){first_iteration=false;}
		else
		{
				disabled = '';
				if (headers[header].toLowerCase().includes('datecreated') || headers[header].toLowerCase().includes('lastconnected'))
				{
						disabled = 'disabled="disabled"';
				}

				if (oddCheck%2==1)
				{
					if (headers[header].toLowerCase().includes('date') || headers[header].toLowerCase().includes('lastconnected'))
					{
						modal +=  '<div class="row"><div class="col-sm"><label>' + headers[header] + '</label></div><div class="col-sm"><div id="date" class="input-group"><input type="text" '+disabled+' class="form-control datepicker_recurring_start" name="' +  headers[header] + '" /><div class="input-group-append"><span class="input-group-text" id="basic-addon2"><i class="fas fa-calendar-alt"></i></span></div></div></div>';
					}
					else
					{
						modal +=  '<div class="row"><div class="col-sm"><label>' + headers[header] + '</label></div><div class="col-sm"><input class="form-control" type="text" name="' +  headers[header] + '" /></div>';
					}
				}
				else
				{
					if (headers[header].toLowerCase().includes('date') || headers[header].toLowerCase().includes('lastconnected'))
					{
						modal +=  '<div class="col-sm"><label>' + headers[header] + '</label></div><div class="col-sm"><div id="date" class="input-group"><input type="text" '+disabled+' class="form-control datepicker_recurring_start" name="' +  headers[header] + '" /><div class="input-group-append"><span class="input-group-text" id="basic-addon2"><i class="fas fa-calendar-alt"></i></span></div></div></div></div><br>';
					}
					else
					{
        				modal +=  '<div class="col-sm"><label>' + headers[header] + '</label></div><div class="col-sm"><input class="form-control" type="text" name="' +  headers[header] + '" /></div></div><br>';
					}
				}
    	}
    	oddCheck++;
	}
		oddCheck--;
	    if(oddCheck%2!=0)
    	{
    		modal+= '<div class="col-sm"></div><div class="col-sm"></div></div>';
    	}
	
	modal += '</form></div><div class="modal-footer"><button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button><button type="button" class="btn btn-primary" data-dismiss="modal" onclick="createRecord(\\''+tablename+'\\');">Create Record</button></div></div></div></div>';
	
	modal += '<div class="modal fade" id="deleteModal" tabindex="-1" role="dialog" aria-hidden="true"><div class="modal-dialog" role="document"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Delete Record</h5><button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button></div><div class="modal-body"><p>Are you sure you want to delete this record?<br>This cannot be undone.</p></div><div class="modal-footer"><button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button><button type="button" class="btn btn-danger" data-dismiss="modal" onclick="deleteRecord(\\''+tablename+'\\');">Delete</button></div></div></div></div>';
	
	modal = modal.replace(/null/g,'');
	
	return modal;
}

function updateRecord(formId, elemId, table){
	$('form:eq('+formId+') *').filter(':input').each(function () {
		if (this.value == ''){this.value='None';}
		if (this.value == ' '){this.value='None';}
	});
	var str = $('form:eq('+formId+')').serialize();
	str = str.replace(/null/g,'None');
	str = str.replace(/\s/g, "None");
	$.ajax({
	  method: "PUT",
	  url: API_BASE + table + "/" + elemId + "?" + str,
	  success: function(dat) {
	  		getData(table,10,0);
		}
	});
}

function deleteRecord(table){
	$.ajax({
	  method: "DELETE",
	  url: API_BASE + table + "/" + elemId,
	  success: function(dat) {
	  		 getData(table,10,0);
		}
	});
}

function createRecord(table){
	$('form[name="createForm"] *').filter(':input').each(function () {
		if (this.value == ''){this.value='None';}
	});
	var str = $('form[name="createForm"]').serialize();
	str = str.replace(/null/g,'None');
	str = str.replace(/\s/g, 'None');
	$.ajax({
	  method: "POST",
	  url: API_BASE + table + "?" + str,
	  success: function(dat) {
	  		getData(table,10,0);
		}
	});	
}

/**
 * Jobs-only: assign driver/vehicle to a job.
 */
function assignJob(jobId, modalIndex) {
	var driverVal = $("#assignDriver" + modalIndex).val();
	var vehicleVal = $("#assignVehicle" + modalIndex).val();
	if (driverVal === "") { driverVal = "None"; }
	if (vehicleVal === "") { vehicleVal = "None"; }

	$.ajax({
		method: "PUT",
		url: API_BASE + "jobs/" + jobId + "/assign?DriverID=" + encodeURIComponent(driverVal) + "&VehicleID=" + encodeURIComponent(vehicleVal),
		success: function() {
			getData("jobs", 10, 0);
		}
	});
}

/**
 * Jobs-only: update lifecycle status.
 */
function setJobStatus(jobId, status) {
	$.ajax({
		method: "PUT",
		url: API_BASE + "jobs/" + jobId + "/status?Status=" + encodeURIComponent(status),
		success: function() {
			getData("jobs", 10, 0);
		}
	});
}

function getRowId(elemModal)
{
	elemId = $('#'+elemModal).val();
}

function setActiveButton(id)
{
	$(".nav-item").removeClass("active");
	$("#nav-"+id).addClass("active");
}

function changePassword()
{
	var oldpas = $('#oldPassword').val();
	var newpas1 = $('#newPassword1').val();
	var newpas2 = $('#newPassword2').val();
	if (newpas1==newpas2)
	{
		$.ajax({
		  method: "PUT",
		  url: (window.location.origin + "/admin/changepassword?oldPassowrd="+encodeURIComponent(oldpas)+"&newPassword="+encodeURIComponent(newpas1)),
		  success: function(dat) {
				if(dat.Status=='Error')
				{
					$('#changePasswordMessage').text(dat.Message);
					$('#oldPassword').val('');
					$('#newPassword1').val('');
					$('#newPassword2').val('');
				}
				else
				{
					$('#changePasswordModal').modal('toggle');
					alert(dat.Message);
					$('#oldPassword').val('');
					$('#newPassword1').val('');
					$('#newPassword2').val('');
				}
		  }
		});
	}
	else
	{
		$('#changePasswordMessage').text("New passwords don't match.");
	}
}

function changePageNum(increment)
{
	if (!isIncremented)
	{
		if (increment)
		{
			isIncremented = true;
			currentPage++;
		}
		else
		{
			isIncremented = true;
			currentPage--;
		}
	}
}

function newPageSort(l1, l2)
{
	currentPage=1;
	buildLink(l1,l2);
}

function buildLink(l1, l2)
{
	isSort=true;
	var e = document.getElementById("selectSortOption");
	var option = e.options[e.selectedIndex].value;
	if(option=='pending'){sortSelected=['selected','',''];}
	if(option=='delivered'){sortSelected=['','selected',''];}
	if(option=='all'){sortSelected=['','','selected'];}
	if (option=='all')
	{
		isSort=false;
		getData('jobs',10,0);
	}
	else
	{
		var link = 'jobs/' + option;
		tablename = 'jobs';
		setActiveButton('jobs');
		$.getJSON(API_BASE + link.toLowerCase(), function(result){
	    	totalNum = result.length;
	    	$.getJSON(API_BASE + link.toLowerCase() + "?limit1="+l1+"&limit2="+l2, function(result){
	    		makeTable(result, l1, l2);
	    	});
	    });
	}
}

// ---- Dashboard charts ----
var _moneyChart = null;
function initMoneyBarChart(rows) {
	var labels = [];
	var revenue = [];
	var receipts = [];
	var largest = 0;

	for (var i=0; i<rows.length; i++) {
		labels.push(rows[i].Month);
		revenue.push(rows[i].Amount);
		receipts.push(rows[i].Receipts);

		if (Number(rows[i].Amount) > largest) { largest = Number(rows[i].Amount); }
		if (Number(rows[i].Receipts) > largest) { largest = Number(rows[i].Receipts); }
	}

	largest = (Math.ceil(largest/500))*500;
	var ctx = document.getElementById("myBarChart");
	if (!ctx) { return; }

	if (_moneyChart) { _moneyChart.destroy(); }

	_moneyChart = new Chart(ctx, {
		type: 'bar',
		data: {
			labels: labels,
			datasets: [{
				label: "Revenue",
				backgroundColor: "#4e73df",
				hoverBackgroundColor: "#2e59d9",
				borderColor: "#4e73df",
				data: revenue
			},{
				label: "Receipts",
				backgroundColor: "#FFA64D",
				hoverBackgroundColor: "#FF8C19",
				borderColor: "#FFA64D",
				data: receipts
			}]
		},
		options: {
			maintainAspectRatio: false,
			layout: { padding: { left: 10, right: 25, top: 25, bottom: 0 } },
			scales: {
				xAxes: [{ gridLines: { display: false, drawBorder: false }, ticks: { maxTicksLimit: 6 }, maxBarThickness: 50 }],
				yAxes: [{ ticks: { min: 0, max: Math.round(largest), maxTicksLimit: 5, padding: 10 } }]
			},
			legend: { display: false }
		}
	});
}

var _workShareChart = null;
function initWorkShareChart(workShare) {
	var labels = [];
	var data = [];
	for (var i=0; i<workShare.length; i++) {
		labels.push(workShare[i].DriverName);
		data.push(workShare[i].Jobs);
	}

	var ctx = document.getElementById("myPieChart");
	if (!ctx) { return; }

	if (_workShareChart) { _workShareChart.destroy(); }

	_workShareChart = new Chart(ctx, {
		type: 'doughnut',
		data: {
			labels: labels,
			datasets: [{
				data: data,
				backgroundColor: ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b', '#858796'],
				hoverBorderColor: "rgba(234, 236, 244, 1)"
			}]
		},
		options: {
			maintainAspectRatio: false,
			legend: { display: false },
			cutoutPercentage: 80
		}
	});
}
