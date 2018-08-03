function filterResults() {
    var input = document.getElementById("resultSearchInput");
    var filter = input.value.toUpperCase();
    var resultsList = document.getElementById("resultsList");
    var results = resultsList.getElementsByClassName("gradient");

    var visibleCount = 0;
    // Loop through all table rows, and hide those who don't match the search query
    for (i = 0; i < results.length; i++) {
        div = results[i];
        if (div.innerHTML.toUpperCase().indexOf(filter) > -1) {
            div.style.display = "block";
            visibleCount++;
        } else {
            div.style.display = "none";
        }
    }
    if (visibleCount < results.length) {
        setResultText('Displaying ' + visibleCount + ' of ');
    } else {
        setResultText('');
    }
}

function setResultText(text) {
    var resultText = document.getElementById("resultDisplayCount");
    resultText.innerHTML = text;
}

function toggleDisplay(elementId) {
    var element = document.getElementById(elementId);
    if (element.style.display === 'none') {
        element.style.display = 'block';
    } else {
        element.style.display = 'none';
    }
}

function deleteExperiment(resultName) {
    if (confirm("Delete experiment " + resultName + "?")) {
        console.log("Deleting experiment " + resultName);
        xhr = new XMLHttpRequest();
        xhr.open('POST', 'delete_job');
        xhr.onload = function() {
            console.log(xhr.responseText);
        }
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.send(JSON.stringify({
            'id': resultName
        }));
    } else {
        console.log('Not deleting ' + resultName);
    }
}

function stopExperiment(resultName) {
    if (confirm("Stop experiment " + resultName + "?")) {
        console.log("Stopping experiment " + resultName);
        xhr = new XMLHttpRequest();
        xhr.open('POST', 'stop_job');
        xhr.onload = function() {
            console.log(xhr.responseText);
        }
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.send(JSON.stringify({
            'id': resultName
        }));
    } else {
        console.log('Not stopping ' + resultName);
    }
}
