// Kupertino layout: a macOS menu bar on top, a dock on the bottom. Applying
// the theme with "Desktop and window layout" ticked removes every panel and
// runs this script, so there is no existing layout to check for here.
//
// addWidget() appends, so creation order *is* the panel order.

// The menu bar: Global Menu, expanding spacer, tray, clock. The spacer is
// load-bearing — the Global Menu applet declares Plasmoid.CanFillArea, so
// without a spacer it is the panel's only expanding element, and when the
// focused app exports no menu (Steam, Electron apps) it collapses to zero
// width and drags the tray and clock left with it.
var menubar = new Panel("org.kde.panel");
menubar.location = "top";
menubar.height = 27;
menubar.alignment = "center";
menubar.lengthMode = "fill";
menubar.hiding = "none";
menubar.floating = false;
menubar.addWidget("org.kde.plasma.appmenu");
var spacer = menubar.addWidget("org.kde.plasma.panelspacer");
spacer.currentConfigGroup = ["General"];
spacer.writeConfig("expanding", true);
menubar.addWidget("org.kde.plasma.systemtray");
menubar.addWidget("org.kde.plasma.digitalclock");

// The dock: the reference machine's bottom panel, centered and fit to its
// contents. Kickoff stays here because kupertino clears the bare-Meta tap.
var dock = new Panel("org.kde.panel");
dock.location = "bottom";
dock.height = 50;
dock.alignment = "center";
dock.lengthMode = "fit";
dock.floating = false;
dock.addWidget("org.kde.plasma.kickoff");
var tasks = dock.addWidget("org.kde.plasma.icontasks");
tasks.currentConfigGroup = ["General"];
tasks.writeConfig("launchers", [
    "preferred://filemanager",
    "preferred://browser",
    "applications:systemsettings.desktop",
]);
dock.addWidget("org.kde.plasma.marginsseparator");
dock.addWidget("org.kde.plasma.showdesktop");

var desktopsArray = desktopsForActivity(currentActivity());
for (var j = 0; j < desktopsArray.length; j++) {
    desktopsArray[j].wallpaperPlugin = "org.kde.image";
}
