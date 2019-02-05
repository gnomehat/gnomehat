/*
 ws-repl
  (c) 2017 Rowan Thorpe

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

function wsrepl(customArgs) {

var defArgs = {
    serverName: '127.0.0.1',
    port: 8080,
    socketProto: 'ws',
    bufferLines: 500,
    replElName: 'output',
    inputElName: 'msg',
    replSendColor: 'white',
    replReplyColor: 'white',
    replOpenBgColor: '#0a0a0a',
    replClosedBgColor: '#933',
    replCursor: '$ ',
    replMargin: '0.4em auto 0.4em 0.4em',
    replPadding: '0.4em',
    replHeight: '640px',
    replWidth: '900px',
    replBorderWidth: '0.1em',
    replBorderColor: '#000',
    replBorderStyle: 'solid',
    replTextAlign: 'left',
    replOverflow: 'auto',
    inputMargin: '0px auto auto 0.4em',
    inputPadding: '0.2em',
    inputWidth: '100%',
    inputHeight: '2em'
};

var arg = Object.assign({}, defArgs, customArgs);

// constants

var splitBuf = [''];
var mainEl  = document.getElementById('repl');
var hiddenEl = document.createElement('textarea');
var replEl = document.createElement('pre');
replEl.setAttribute('id', arg.replElName);
var inputEl = document.createElement('input');
inputEl.setAttribute('id', arg.inputElName);
inputEl.setAttribute('type', 'text');
inputEl.setAttribute('autofocus', 'autofocus');
inputEl.setAttribute('tabindex', '1');
var sty = document.createElement('style');
sty.setAttribute('rel', 'stylesheet');
sty.setAttribute('type', 'text/css');

// functions

function htmlEncode(str) {
    hiddenEl.innerHTML = str;
    return hiddenEl.innerHTML;
}

function htmlDecode(str) {
    hiddenEl.innerHTML = str;
    return hiddenEl.childNodes.length === 0 ? '' : hiddenEl.childNodes[0].nodeValue;
}

function replyToPage(str) {
    // TODO: is there an easy way to keep a ring buffer of divs?
    var len = splitBuf.length;
    if (len > arg.bufferLines) {
        for (var i = 0; i < len - 1; i++) {
            splitBuf[i] = splitBuf[i+1];
        }
    } else {
        splitBuf[len] = '';
    }
    splitBuf[len - 1] = '<span style="color:' + arg.replReplyColor + '">' + htmlEncode(str) + '</span>';

    replEl.innerHTML = splitBuf.join('') + arg.replCursor;
    replEl.scrollTop = 999999;
}

// main

sty.innerHTML = '#' + arg.replElName + ' {\n margin: ' + arg.replMargin + ';\n padding: ' + arg.replPadding + ';\n height: ' + arg.replHeight + ';\n width: ' + arg.replWidth + ';\n color: ' + arg.replSendColor + ';\n background-color: ' + arg.replClosedBgColor + ';\n border-width: ' + arg.replBorderWidth + ';\n border-color: ' + arg.replBorderColor + ';\n border-style: ' + arg.replBorderStyle + ';\n text-align: ' + arg.replTextAlign + ';\n overflow: ' + arg.replOverflow + ';\n}\n#' + arg.inputElName + ' {\n margin: ' + arg.inputMargin + ';\n padding: ' + arg.inputPadding + ';\n width: ' + arg.inputWidth + ';\n height: ' + arg.inputHeight + ';\n}';
document.getElementsByTagName('head')[0].appendChild(sty);

var ws = new WebSocket(arg.socketProto + '://' + arg.serverName + ':' + arg.port);
ws.addEventListener('open', function (event) { replEl.style.backgroundColor = arg.replOpenBgColor; });
ws.addEventListener('message', function (event) { replyToPage(event.data, true); });
ws.addEventListener('close', function (event) { replEl.style.backgroundColor = arg.replClosedBgColor; });

mainEl.appendChild(replEl);
}
