replace(
  if(
    contains(variables('varMessageLink'), '&amp;'),
    replace(variables('varMessageLink'), '&amp;', '&'),
    variables('varMessageLink')
  ),
  ' ', '%20'
)
