const constraints = { 
    width: {
        exact: 640 
    }, 
    height: { 
        exact:360 
    }, 
    frameRate: { 
        exact: 30 
    }
}

/* -------------------------------------------------------------------------- */
/*                  Request Permissions and Enumerate Devices                 */
/* -------------------------------------------------------------------------- */

async function enumerateDevices() {
    try {
        let devices = await navigator.mediaDevices.enumerateDevices();
        devices.forEach(function(device, index) {
            console.log(device);
            if (device.deviceId != null && device.kind == 'videoinput') {
                let menu = $('#select-media-source')
                let item = document.createElement("option");
                item.innerText = device.label;
                item.value = device.deviceId;
                menu.append(item);
            }
        });
        $('#div-error').html($('#div-error').html() + '<br>' + 'Success List Devices');
    }
    catch {
        $('#div-error').html($('#div-error').html() + '<br>' + err.name + ": " + err.message);
    }
}

navigator.mediaDevices.getUserMedia({ video: true }).then(enumerateDevices);

/* -------------------------------------------------------------------------- */
/*                               Stream Handler                               */
/* -------------------------------------------------------------------------- */
var pc = null;

function negotiate () {
	return pc.createOffer().then(function (offer) {
		return pc.setLocalDescription(offer);
	}).then(function () {
		// wait for ICE gathering to complete
		return new Promise(function (resolve) {
			if (pc.iceGatheringState === 'complete') {
				resolve();
			} else {
				function checkState () {
					if (pc.iceGatheringState === 'complete') {
						pc.removeEventListener('icegatheringstatechange', checkState);
						resolve();
					}
				}
				pc.addEventListener('icegatheringstatechange', checkState);
			}
		});
	}).then(function () {
		var offer = pc.localDescription;
		return fetch('/offer', {
			body: JSON.stringify({
				sdp: offer.sdp,
				type: offer.type,
                device: $('#select-target-device :selected').val(),
			}),
			headers: {
				'Content-Type': 'application/json'
			},
			method: 'POST'
		});
	}).then(function (response) {
		return response.json();
	}).then(function (answer) {
		return pc.setRemoteDescription(answer);
	}).catch(function (e) {
		alert(e);
	});
}


function streamStart() {
    let mediaSource = $('#select-media-source :selected').val();
    console.log(mediaSource);
    let mediaStreamConstraints = { video: { deviceId: { exact: mediaSource }}};
    navigator.mediaDevices.getUserMedia(mediaStreamConstraints).then(function(stream) {
        const track = stream.getVideoTracks()[0];
        track.applyConstraints(constraints).then(function() {
            $('#btn-stream-start').prop('disabled', true);
            $('#video-stream').prop('srcObject', stream);
            pc = new RTCPeerConnection({ sdpSemantics: 'unified-plan' });
            pc.addTransceiver(stream.getVideoTracks()[0], {direction: 'sendonly'});
            negotiate();
        }).then(function(){
            $('#btn-stream-stop').prop('disabled', false);
        }).catch(function(err) {
            alert(err);
            $('#btn-stream-start').prop('disabled', false);
            $('#btn-stream-stop').prop('disabled', true);
        });
    });
    
}

function streamStop() {
    // close peer connection
    setTimeout(function() {
        pc.close();
    }, 500);
    $('#btn-stream-start').prop('disabled', false);
    $('#btn-stream-stop').prop('disabled', true);
    $('#video-stream').prop('srcObject').getVideoTracks().forEach(track => track.stop());
    $('#video-stream').prop('srcObject', null);
}

$('#btn-stream-start').click(streamStart);
$('#btn-stream-stop').click(streamStop);

/* -------------------------------------------------------------------------- */
/*                             Get Target Devices                             */
/* -------------------------------------------------------------------------- */

$.ajax({
    url: '/get_devices',
    type: 'GET',
    success: function(devices) {
        console.log(devices);
        devices.forEach(function(device, index) {
            let menu = $('#select-target-device')
            let item = document.createElement("option");
            item.innerText = device.name;
            item.value = device.path;
            menu.append(item);
        });
    }
});


