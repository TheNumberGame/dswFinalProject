$(document).ready( function(){
     $(".toTextBox").click( function(){
          var textBox = "<form id=\"replyForm\" action=\"/reply\" enctype=\"multipart/form-data\" method=\"post\"><textarea name=\"message\" form=\"replyForm\" style=\"width:100%; height:100px;\"></textarea><br><input name=\"file\" type=\"file\" form=\"replyForm\"><br><input type=\"submit\" value=\"Post\"></form>"
          $(this).replaceWith(textBox);
     });
});
