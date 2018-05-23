$(document).ready( function(){
    $("form").submit(function () {
        if ($(this).valid()) {
            $(this).submit(function () {
                return false;
            });
            return true;
        }
        else{
            return false;
        }
    });
     $(".toTextBox").click( function(){
          var tempId = $(this).val();
          var textBox = "<textarea name=\"message\" form=\"replyForm\" style=\"width:100%; height:100px;\"></textarea><br><input name=\"file\" type=\"file\" form=\"replyForm\"><br><input type=\"hidden\" name=\"MainPost\" value=\""+ tempId +"\" form=\"replyForm\"><input type=\"submit\" value=\"Post\" form=\"replyForm\">"
          $(this).replaceWith(textBox);
     });
});
