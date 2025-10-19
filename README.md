0) Trigger

Create → Automated cloud flow
Trigger: Microsoft Teams — When a new channel message is added (V3)

Team: (your team)

Channel: (e.g., Anita)

1) Variables (7)

Add Initialize variable ×7 (Name / Type / Value):

varMessageLink / String / (blank)

varHasImage / Boolean / false

varFileName / String / (blank)

varFileExt / String / (blank)

varAffectedUser / String / (blank)

varScreenshotURL / String / (blank)

varListItemId / String / (blank)

2) Extract message info

Action: Teams — Get message details (V3)

Message ID: Message ID (from trigger)

Team/Channel: same as trigger

Action: Set variable → varMessageLink = Link to message (from Get message details)
Action: Set variable → varAffectedUser = From Display Name (from Get message details)

We’ll reuse varAffectedUser for the file name and list fields.

3) Check attachments (any?)

Action: Condition (boolean expression):

length(triggerOutputs()?['body/attachments']) > 0


True branch = has at least one attachment

False branch = no attachment

4) TRUE branch → find the first image and capture its filename

Action: Apply to each

Input: Attachments (from the trigger)

Inside the loop:

Condition (is attachment an image?)

startsWith(coalesce(items('Apply_to_each')?['contentType'],''),'image')


If True:

Set variable → varHasImage = true

Set variable → varFileName = (Expression)

coalesce(items('Apply_to_each')?['name'],'attachment')


Set variable → varFileExt = (Expression)

last(split(variables('varFileName'),'.'))


If False: do nothing

You only need the first image; it’s fine if the last wins in the loop.

5) TRUE branch → try to save the image into your library

We’ll attempt to read the bytes from the Team’s channel folder (where Teams stores message attachments) and create a copy in your library sjrb migration screenshots.
If we can’t read it (e.g., it wasn’t stored in Files), we’ll gracefully fall back in Step 6.

Condition (boolean):

and(variables('varHasImage'), not(empty(variables('varFileName'))))

If True → attempt copy into your library

SharePoint — Get file content using path (attempt #1)

Site Address: the Team’s site behind the channel (use “Open in SharePoint” from that channel’s Files tab once to confirm)

File Path (Expression):

concat('/Shared Documents/Anita/', variables('varFileName'))


(If your tenant uses /Documents/Anita/, add a second “Get file content using path” with that path and set fallback run-after as below.)

SharePoint — Create file (your Support site where the destination library lives)

Site Address: your site (e.g., https://contoso.sharepoint.com/sites/Support)

Folder Path: /sjrb migration screenshots/

File Name (Expression):

concat(
  replace(variables('varAffectedUser'),' ','_'),
  '_Screenshot_',
  formatDateTime(utcNow(),'yyyy-MM-dd'),
  '.',
  variables('varFileExt')
)


File Content: File Content (from Get file content using path)

SharePoint — Update file properties (tag your custom column)

Library Name: sjrb migration screenshots

Id: ID (from Create file)

Affected User: variables('varAffectedUser')

SharePoint — Get file metadata

File Identifier: Identifier (from Create file)

Set variable → varScreenshotURL = Link to item (from Get file metadata)

Run-after (important):

On Create file, set Configure run after to also run after failure of the first Get file content (so you can add an attempt #2 with /Documents/… if needed).

If both attempts fail, we’ll fall back in Step 6.

If False → skip to Step 6 (no usable image)
6) Fallback (runs when there’s no image or we couldn’t read it)

We still create a message record file in your library so the card/list always have a SharePoint link (never a Graph URL).

Compose — MessageRecordContent (Expression)

concat(
  'From: ', variables('varAffectedUser'), '\n',
  'Posted (UTC): ', utcNow(), '\n',
  'Original Message Link: ', variables('varMessageLink'), '\n\n',
  'Message Body:\n', outputs('Get_message_details_(V3)')?['body']
)


SharePoint — Create file (your site)

Folder Path: /sjrb migration screenshots/

File Name (Expression):

concat(
  replace(variables('varAffectedUser'),' ','_'),
  '_Message_',
  formatDateTime(utcNow(),'yyyy-MM-dd'),
  '.txt'
)


File Content: Outputs of Compose — MessageRecordContent

SharePoint — Update file properties

Library Name: sjrb migration screenshots

Id: ID (from Create file)

Affected User: variables('varAffectedUser')

SharePoint — Get file metadata

File Identifier: Identifier (from Create file)

Set variable → varScreenshotURL = Link to item (from Get file metadata)

This gives you a valid SharePoint link even without an image.

7) Create the Combined Log item

Action: SharePoint — Create item

List: Combined Log

Map:

Affected User Name → variables('varAffectedUser')

Description → Body (from Get message details)

Screenshot Attached? → variables('varHasImage')

Screenshot (Hyperlink) → Url = variables('varScreenshotURL'), Description = Open Item

Date Reported → Expression utcNow()

(Others as needed)

Set variable → varListItemId = ID (from Create item)

8) Post the Adaptive Card to your support chat

We’ll show View Screenshot only when we actually have a link (we do—either an image file or the message record).

Condition (optional safety):

not(empty(variables('varScreenshotURL')))


True → Post adaptive card and wait for a response

Post as: Flow bot

Post in: Group chat (your support chat)

Message (JSON) — paste, then bind the placeholders as noted:

{
  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
  "type": "AdaptiveCard",
  "version": "1.5",
  "body": [
    { "type": "TextBlock", "text": "**New Issue Reported**", "weight": "Bolder", "size": "Medium" },
    { "type": "TextBlock", "text": "Affected User: ${AffectedUserName}", "wrap": true },
    { "type": "TextBlock", "text": "Description: ${Description}", "wrap": true }
  ],
  "actions": [
    { "type": "Action.Submit", "title": "Work in Progress", "data": { "action": "assignToMe", "listItemId": "${ListItemID}" } },
    { "type": "Action.OpenUrl", "title": "View Screenshot", "url": "${ScreenshotURL}" },
    { "type": "Action.OpenUrl", "title": "View Original Message", "url": "${MessageURL}" }
  ]
}


Bind:

${AffectedUserName} → variables('varAffectedUser')

${Description} → Body (Get message details)

${ListItemID} → variables('varListItemId')

${ScreenshotURL} → variables('varScreenshotURL')

${MessageURL} → variables('varMessageLink')

(If you want an Issue line too, add it in your list + mapping.)

9) On Work in Progress → set Agent Name (Person) + post follow-ups

Condition:

equals(body('Post_adaptive_card_and_wait_for_a_response')?['data']?['action'],'assignToMe')


True branch:

SharePoint — Update item (Combined Log)

Id: variables('varListItemId')

Agent Name (Person) = claims (Expression):

concat(
  'i:0#.f|membership|',
  body('Post_adaptive_card_and_wait_for_a_response')?['responder']?['userPrincipalName']
)


(If your tenant accepts plain UPN, you can instead use the UPN value directly.)

Teams — Post message in a chat or channel (Group chat: your support chat)

🛠️ @{body('Post_adaptive_card_and_wait_for_a_response')?['responder']?['displayName']}
is working on the issue.
🔗 Original: @{variables('varMessageLink')}


Teams — Reply with a message in a channel

Message ID: from the trigger

Message:

🛠️ A technician is now working on your issue. We’ll keep you updated!
