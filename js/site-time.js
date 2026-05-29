(function () {
  var MONTHS_GEN = [
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
  ];
  var WEEKDAYS = [
    "воскресенье",
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
  ];

  function pad(n) {
    return String(n).padStart(2, "0");
  }

  function formatHiddenHeaderDate(d) {
    return (
      d.getDate() + " " + MONTHS_GEN[d.getMonth()] + ", " + WEEKDAYS[d.getDay()]
    );
  }

  function formatBlackBar(d) {
    return (
      pad(d.getHours()) +
      ":" +
      pad(d.getMinutes()) +
      " " +
      pad(d.getDate()) +
      "." +
      pad(d.getMonth() + 1) +
      "." +
      d.getFullYear()
    );
  }

  function formatTimeHM(d) {
    return pad(d.getHours()) + ":" + pad(d.getMinutes());
  }

  function formatArticleDate(d) {
    return d.getDate() + " " + MONTHS_GEN[d.getMonth()] + " " + d.getFullYear();
  }

  function isoLocal(d) {
    return (
      d.getFullYear() +
      "-" +
      pad(d.getMonth() + 1) +
      "-" +
      pad(d.getDate()) +
      "T" +
      pad(d.getHours()) +
      ":" +
      pad(d.getMinutes()) +
      ":" +
      pad(d.getSeconds())
    );
  }

  function tick() {
    var now = new Date();

    document.querySelectorAll(".datetime-black-bar").forEach(function (el) {
      el.textContent = formatBlackBar(now) + " ";
      el.setAttribute("datetime", isoLocal(now));
    });

    document.querySelectorAll(".hidden-time").forEach(function (el) {
      el.textContent = formatTimeHM(now);
      var parent = el.closest("time");
      if (parent) parent.setAttribute("datetime", isoLocal(now));
    });

    document.querySelectorAll(".hidden-date").forEach(function (el) {
      el.textContent = formatHiddenHeaderDate(now);
    });
  }

  tick();
  setInterval(tick, 1000);
})();
