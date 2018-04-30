$(document).ready( function(){
     $(".toTextBox").click( function(){
          var textBox = "<textarea name=\"message\" form=\"replyForm\" style=\"width:100%; height:100px;\"></textarea><br><input name=\"file\" type=\"file\" form=\"replyForm\"><br><input type=\"submit\" value=\"Post\" form=\"replyForm\">"
          $(this).replaceWith(textBox);
     });
});
