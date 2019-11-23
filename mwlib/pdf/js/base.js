Prince.trackBoxes = true;
Prince.addEventListener("complete", analyze, false);

function analyze() {
    var obj = document.getElementsByTagName('html')[0];
    htmlTree(obj);
    Log.data("total-page-count", Prince.pageCount);
}


function htmlTree(obj) {
    var bx = obj.getPrinceBoxes();
    console.log(obj.tagName + " boxid: " + obj.getAttribute("boxid"));
    showbox(bx);
    if (obj.hasChildNodes()) {
        var child = obj.firstChild;
        while (child) {
            if (child.nodeType === 1) {
                htmlTree(child);
            }
            child = child.nextSibling;
        }
    }
}

function showbox(bx) {
    console.log("  #boxes: " + bx.length);
    for (var j = 0; j < bx.length; j++) {
        console.log("  box: " + j);
        console.log("width: " + bx[j]["w"]);
        console.log("height: " + bx[j]["h"]);
        // for (var i in bx[j])
        // {
        //     console.log("    "+i+": "+bx[j][i]);
        // }
    }
}
