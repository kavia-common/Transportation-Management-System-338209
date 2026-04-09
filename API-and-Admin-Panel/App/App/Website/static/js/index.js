window.onload = function () {
  defaultMap(53.479593, -2.22373);
};

// Get the location variables
function getLocationVars(stringURL) {
  $.getJSON(stringURL, function (data) {
    var str = data[0].Location;
    var loc = str.split(",", 2);
    var text = "Your driver is: " + data[0].FirstName;
    $(".mypanel").html(text);
    trackingMap(loc[0], loc[1]);
  });
}

// Form validation
function getLocation() {
  var x = document.getElementById("trackingID").value;
  if (x == "") {
    alert("Enter a valid tracking number!");
    return false;
  } else {
    var trackID = x;
    // Same-origin API call for preview environment compatibility.
    var trackData = "/api/jobs/" + encodeURIComponent(trackID) + "/location";
    getLocationVars(trackData);
  }
}

// Google Maps

function defaultMap(lat, lng) {
  var myLatLng = new google.maps.LatLng(lat, lng);
  var mapProp = {
    center: myLatLng,
    zoom: 6,
    disableDefaultUI: true,
  };
  new google.maps.Map(document.getElementById("googleMap"), mapProp);
}

function trackingMap(lat, lng) {
  var myLatLng = new google.maps.LatLng(lat, lng);
  var mapProp = {
    center: myLatLng,
    zoom: 14,
    disableDefaultUI: true,
  };
  var map = new google.maps.Map(document.getElementById("googleMap"), mapProp);
  new google.maps.Marker({
    position: myLatLng,
    // Same-origin static asset URL.
    icon: "/home/static/img/truck.png",
    map: map,
  });
}
