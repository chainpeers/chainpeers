var chart;
var url;
fetch('./static/settings.json')
    .then((response) => response.json())
    .then((json) => url = json.address);
function loadData() {
    var version = document.getElementById('version').value;
    axios.get(url + '/peers/' + version)
        .then(function (response) {
            var peers = response.data.peers;
            var labels = peers.map(function(peer) { return peer.time; });
            console.log(labels)
            var data = peers.map(function(peer) { return Number(peer.score); });

            // destroy the old chart if it exists
            if (chart) {
                chart.destroy();
            }

            // count the number of peers with the same data and score
            var counts = {};
            for (var i = 0; i < peers.length; i++) {
                var key = peers[i].time + '-' + Number(peers[i].score);
                counts[key] = (counts[key] || 0) + 1;

            }

            var ctx = document.getElementById('chart').getContext('2d');
            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Score',
                        data: data,
                        fill: false,
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1,

                    }]
                },
            });

            // update the addresses div
            var addresses = peers.map(function(peer) { return peer.address; }).join('<br>');
            document.getElementById('addresses').innerHTML = addresses;
        })
        .catch(function (error) {
            console.log(error);
        });
}