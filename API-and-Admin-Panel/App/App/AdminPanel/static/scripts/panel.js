var tablename;
var elemId;
var totalNum;
var currentPage = 1;
var sortSelected = ['', '', 'selected'];
var isSort = false;
var isIncremented = false;

$('body').on('focus', ".datepicker_recurring_start", function () {
    $(this).datetimepicker({ defaultDate: new Date(), format: 'YYYY-MM-DD HH:mm:ss', sideBySide: true });
});

function newPage(data, l1, l2) {
    currentPage = 1;
    isSort = false;
    getData(data, l1, l2);
}

function getData(data, l1, l2) {
    if (!isSort) {
        tablename = data;
        setActiveButton(data);
        $.getJSON("/api/" + data, function (result) {
            totalNum = result.length;
            $.getJSON("/api/" + data + "?limit1=" + l1 + "&limit2=" + l2, function (result) {
                makeTable(result, l1, l2);
            });
        });
    }
    else {
        buildLink(l1, l2);
    }
}

function getHeaders(result) {
    var headers = [];
    $.each(result, function (key, value) {
        headers.push(key);
    });
    return headers;
}

function makeTable(result, l1, l2) {
    isIncremented = false;
    var modalIndex = 0;
    $('#pageHeader').html(tablename.charAt(0).toUpperCase() + tablename.slice(1));
    $('#pageContent').css("margin-right", "15px");

    var table = '<div style="margin-left:5px;" class="row"><div class="col-xl-3 col-md-6 mb-4"><div class="card card-hover border-left-primary shadow h-10 py-2" data-toggle="modal" data-target="#addModal" style="cursor: pointer;"><div class="card-body"><div class="row no-gutters align-items-center"><div class="col mr-2"><div class="text-xs font-weight-bold text-primary text-uppercase mb-1">Add</div><div class="h5 mb-0 font-weight-bold text-gray-800">Create Record</div></div><div class="col-auto"><i class="fas fa-plus fa-2x text-gray-300"></i></div></div></div></div></div>';
    table += '<div class="col-xl-3 col-md-6 mb-4"><div class="card border-left-success shadow h-10 py-2"><div class="card-body"><div class="row no-gutters align-items-center"><div class="col mr-2"><div class="text-xs font-weight-bold text-success text-uppercase mb-1">Number of ' + tablename + '</div><div class="h5 mb-0 font-weight-bold text-gray-800">' + totalNum + '</div></div><div class="col-auto"><i class="fas fa-warehouse fa-2x text-gray-300"></i></div></div></div></div></div>';

    if (tablename == 'jobs') {
        table += '<div class="col-xl-3 col-md-6 mb-4"><div class="card border-left-info shadow h-10 py-2" style="height:103px;"><div class="card-body"><div class="row no-gutters align-items-center"><div class="col mr-2"><div class="text-xs font-weight-bold text-info text-uppercase mb-1">Sort Table</div><div class="h5 mb-0 font-weight-bold text-gray-800"><div class="form-group"><select id="selectSortOption" class="form-control" data-role="select-dropdown" data-profile="minimal" onchange="newPageSort(10,0);"><option ' + sortSelected[0] + 'value="pending">Pending</option><option ' + sortSelected[1] + ' value="delivered">Delivered</option><option ' + sortSelected[2] + ' value="all">All</option></select></div></div></div><div class="col-auto" style="top:-14px;"><i class="fas fa-sort fa-2x text-gray-300"></i></div></div></div></div></div>';
    }
    table += '</div>';
    table += '<p style="margin-left:18px;">The table does not show all the values in a record. Click on a record to see them all and perform updates.</p>';

    table += '<div style="width:auto;margin:18px;" class="card border-left-warning shadow"><table class="table table-hover"><thead><tr>';
    var headers = getHeaders(result[0]);
    var modals = makeModals(result);
    var picModals = '';

    var i = 0;
    for (var header in headers) {
        if (i < 8) {
            table += '<th scope="col">' + headers[header] + '</th>';
            i++;
        }
    }
    table += '</tr></thead><tbody>';

    var picId = 1;
    $.each(result, function (key, value) {
        table += '<tr>';
        i = 0;
        for (var index in value) {
            if (i < 8) {
                var t = '' + value[index];
                if (t.toLowerCase().includes('.jpg') || t.toLowerCase().includes('.png') || t.toLowerCase().includes('.gif')) {
                    table += '<td><a style="margin-left:5px;height:30px;cursor:pointer;" data-toggle="modal" data-target="#modalPic' + picId + '" class="text-primary"><i class="fas fa-camera"></i> View picture</a></td>';

                    picModals += '<div class="modal fade" id="modalPic' + picId + '" tabindex="-1" role="dialog" aria-labelledby="myModalLabel"><div class="modal-dialog" role="document"><div class="modal-content"><div class="modal-header"><h4 class="modal-title" id="myModalLabel">Picture</h4><button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button></div><div class="modal-body"><a href="' + value[index] + '" target="_blank"><img style="display:block;width:90%;margin:auto;" src="' + value[index] + '" /></a></div><div class="modal-footer"><button type="button" class="btn btn-dark" data-dismiss="modal">Close</button></div></div></div></div>';
                    picId++;
                }
                else {
                    table += '<td data-toggle="modal" data-target="#modal' + modalIndex + '" style="cursor: pointer;">' + value[index] + '</td>';
                }
                i++;
            }
        }
        table += '</tr>';
        modalIndex++;
    });

    table += '</tbody></table></div>';
    table = table.replace(/null/g, '');
    var totalPages = Math.ceil(totalNum / 10);
    if (l2 == 0) {
        if (result.length < 10) {
            table += '<footer><div><div><h3 style="cursor:default;" class="d-inline"><span class="badge badge-secondary"><i class="fas fa-angle-left"></i></span></h3>';
            table += '&nbsp;<h3 style="cursor:default;" class="d-inline"><span class="badge badge-secondary"><i class="fas fa-angle-right"></i></span></h3><div style="width:150px;">Page ' + currentPage + ' of ' + totalPages + '</div></div></div></footer>';
        }
        else {
            table += '<footer><div><div><h3 style="cursor:default;" class="d-inline"><span class="badge badge-secondary"><i class="fas fa-angle-left"></i></span></h3>';
            l2 += 10;
            table += '&nbsp;<h3 class="d-inline" onclick="getData(\'' + tablename + '\',' + l1 + ',' + l2 + ');changePageNum(true);"><span class="badge badge-primary"><i class="fas fa-angle-right"></i></span></h3><div style="width:150px;">Page ' + currentPage + ' of ' + totalPages + '</div></div></div></footer>';
        }
    }
    else {
        if (result.length < 10) {
            l2 -= 10;
            table += '<footer><div><div><h3 class="d-inline" onclick="getData(\'' + tablename + '\',' + l1 + ',' + l2 + ');changePageNum(false);"><span class="badge badge-primary"><i class="fas fa-angle-left"></i></span></h3>';
            table += '&nbsp;<h3 style="cursor:default;" class="d-inline"><span class="badge badge-secondary"><i class="fas fa-angle-right"></i></span></h3><div style="width:150px;">Page ' + currentPage + ' of ' + totalPages + '</div></div></div></footer>';
        }
        else {
            l2 -= 10;
            table += '<footer><div><div><h3 class="d-inline" onclick="getData(\'' + tablename + '\',' + l1 + ',' + l2 + ');changePageNum(false);"><span class="badge badge-primary"><i class="fas fa-angle-left"></i></span></h3>';
            l2 += 20;
            table += '&nbsp;<h3 class="d-inline" onclick="getData(\'' + tablename + '\',' + l1 + ',' + l2 + ');changePageNum(true);"><span class="badge badge-primary"><i class="fas fa-angle-right"></i></span></h3><div style="width:150px;">Page ' + currentPage + ' of ' + totalPages + '</div></div></div></footer>';
        }
    }

    $("#pageContent").html(table);
    $("#modals").html(modals + picModals);
}

// The rest of the code (makeModals, updateRecord, deleteRecord, createRecord, etc.) would remain unchanged, with URLs
// changed from "http://soc-web-liv-82.napier.ac.uk/api/" to "/api/" and "http://soc-web-liv-82.napier.ac.uk/admin/"
// to "/admin/" (and similar for changePassword, etc.). For brevity, the detailed modals and AJAX functions are omitted
// here but should be copied over from the original, updating ONLY the URLs referenced to use relative paths.
// If more details are needed, request the full consolidation or specify the function to expand.
