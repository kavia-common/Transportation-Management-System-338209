var labels = [];
var revenue = [];
var receipts = [];
var largest = 0;
$.getJSON("/api/money", function(result){
    for (var i=0; i<result.length; i++)
    {
      labels.push(result[i].Month);
      revenue.push(result[i].Amount);
      receipts.push(result[i].Receipts);
      if (Number(result[i].Amount)>largest){largest=Number(result[i].Amount)}
      if (Number(result[i].Receipts)>largest){largest=Number(result[i].Receipts)}
    }
  largest = (Math.ceil(largest/500))*500;
  initChart();
 });

function initChart()
{

// Bar Chart Example
var ctx = document.getElementById("myBarChart");
var myBarChart = new Chart(ctx, {
  type: 'bar',
  data: {
    labels: labels,
    datasets: [{
      label: "Revenue",
      backgroundColor: "#4e73df",
      hoverBackgroundColor: "#2e59d9",
      borderColor: "#4e73df",
      data: revenue,
    },
    {
      label: "Receipts",
      backgroundColor: "#FFA64D",
      hoverBackgroundColor: "#FF8C19",
      borderColor: "#FFA64D",
      data: receipts,
    }],
  },
  options: {
    maintainAspectRatio: false,
    layout: {
      padding: {
        left: 10,
        right: 25,
        top: 25,
        bottom: 0
      }
    },
    scales: {
      xAxes: [{
        time: {
          unit: 'month'
        },
        gridLines: {
          display: false,
          drawBorder: false
        },
        ticks: {
          maxTicksLimit: 6
        },
        maxBarThickness: 50,
      }],
      yAxes: [{
        ticks: {
          min: 0,
          max: Math.round(largest),
          maxTicksLimit: 5,
          padding: 10,
          // Include a pound sign in the ticks
          callback: function(value, index, values) {
            return '\u00a3' + number_format(value);
          }
        },
        gridLines: {
          color: "rgb(234, 236, 244)",
          zeroLineColor: "rgb(234, 236, 244)",
          drawBorder: false,
          borderDash: [2],
          zeroLineBorderDash: [2]
        }
      }],
    },
    legend: {
      display: false
    },
    tooltips: {
      titleMarginBottom: 10,
      titleFontColor: '#6e707e',
      titleFontSize: 14,
      backgroundColor: "rgb(255,255,255)",
      bodyFontColor: "#858796",
      borderColor: '#dddfeb',
      borderWidth: 1,
      xPadding: 15,
      yPadding: 15,
      displayColors: false,
      caretPadding: 10,
      callbacks: {
        label: function(tooltipItem, chart) {
          var datasetLabel = chart.datasets[tooltipItem.datasetIndex].label || '';
          return datasetLabel + ': \u00a3' + number_format(tooltipItem.yLabel);
        }
      }
    },
  }
});
}
