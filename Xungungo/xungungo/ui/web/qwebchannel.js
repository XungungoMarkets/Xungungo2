(function () {
  const script = document.createElement('script');
  script.src = 'qrc:///qtwebchannel/qwebchannel.js';
  script.onload = function () {
    if (window.onQtWebChannelReady) {
      window.onQtWebChannelReady();
    }
  };
  document.head.appendChild(script);
})();
