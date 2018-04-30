$(document).ready( function(){
     $(".toTextBox").click( function(){
          var textBox = "<form action=\"/reply\" enctype=\"multipart/form-data\" method=\"post\"><textarea name=\"message\" style=\"width:100%; height:100px;\"></textarea><br><input name=\"file\" type=\"file\"><br><input type=\"submit\" value=\"Post\"></form>"
          $(this).replaceWith(textBox);
     });
});
