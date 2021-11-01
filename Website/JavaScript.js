function setWindowSize() {

  //document.images["leftpillar"].height = window.innerHeight;
  document.images["rightpillar"].height = window.innerHeight;
  document.images["lefttopbar"].width = window.innerWidth * 0.7;
  document.images["righttopbar"].width = window.innerWidth * 0.7;

  document.getElementById("FolderSidebar").width = document.images["leftpillar"].width;
  document.getElementById("FolderSidebar").height = window.innerHeight - document.images["lefttopbar"].height;
  document.getElementById("FolderSidebar").style.top = document.images["lefttopbar"].height;

  document.getElementById("codescript").style.width = window.innerWidth - 2 * document.images["rightpillar"].width;
  document.getElementById("codescript").style.left = document.images["leftpillar"].width - 1;
  document.getElementById("title").style.left = document.images["leftpillar"].width + 5;
}
setWindowSize()
// var fs = document.getElementById("FolderSidebar");
// // fs.contentDocument.onload = ()=> window.open('https://javascript.info/');
// window.alert(fs.contentDocument);
// fs.contentDocument.body.addEventListener("onclick", function(){
//   window.alert("sometext");
// });

var ChangeCodeFile = function(file, name) {
  document.getElementById("codescript").data=file;
  document.getElementById("title").innerHTML = name;
}
