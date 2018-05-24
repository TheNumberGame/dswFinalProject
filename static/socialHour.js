$(document).ready( function(){
     $('input[type="submit"]').click(function () {
          $(this).append('<img id="loaderImage" src="static/ajax-loader.gif" />');
          $(this).hide();
     });
     $('button[type="submit"]').click(function () {
          $(this).parent().append('<img id="loaderImage" src="static/ajax-loader.gif" />');
          $(this).hide();
     });
     $(".toTextBox").click( function(){
          var tempId = $(this).val();
          var textBox = "<div id=\"replyForm\"><textarea name=\"message\" form=\"replyForm\" style=\"width:100%; height:100px;\"></textarea><br><input name=\"file\" type=\"file\" form=\"replyForm\"><br><input type=\"hidden\" name=\"MainPost\" value=\""+ tempId +"\" form=\"replyForm\"><input type=\"submit\" value=\"Post\" form=\"replyForm\"></div>"
          $(this).replaceWith(textBox);
     });
});
