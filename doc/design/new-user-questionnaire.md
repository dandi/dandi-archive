# Premise
Currently, anyone with a GitHub account can signup for DANDI and make full use of its functionality. The goal of this design document is to introduce an
approval process to help prevent misuse of the archive.

## 1. Implementation Details
### Changes to User model
Three new columns, `status`, `questionnaire_form`, and `rejection_reason` will be introduced to the `User` model in dandi-api.
- `status` is an enum that can be one of four values: `INCOMPLETE`, `PENDING`, `APPROVED`, or `REJECTED`.
- `questionnaire_form` is a JSON field. The keys are questions, and the values are the users' answers.
- `rejection_reason` is an optional string that contains a message written by one of the admins describing why a user was denied approval (if applicable).

### Changes to API
- /users/me needs to include the user's current status
- A [Django group](https://docs.djangoproject.com/en/3.2/topics/auth/default/#groups), `approved_users`, will be created. Only users in this group will have access to protected endpoints.
- Only approved users can create and edit dandisets.
- /users/search endpoint will only return users in the `approved_users` group.

### Changes to frontend
- Configuration so the frontend knows where to find SSR pages
- User avatar circley thing needs to show user's current status

### New views
- SSR rendered pages for questionnaire form, pending approval page, rejected page, and admin approval page.

## 2. High-level Overview
### Current user signup flow
1) The user navigates to https://gui.dandiarchive.org and clicks the "LOG IN WITH GITHUB" button
2) The user is redirected to GitHub, enters their credentials, and clicks "Sign in". This action creates a new DANDI Archive account for the user and gives
them full capabilities of any other normal user (creating/editing dandisets, etc).
3) The user is redirected back to https://gui.dandiarchive.org signed in to their new account.

### Proposed user signup flow
1) The user navigates to https://gui.dandiarchive.org and clicks the "LOG IN WITH GITHUB" button.
2) The user is redirected to GitHub, enters their credentials, and clicks "Sign in". This action creates a new DANDI archive account for the user with the `status` field set to `INCOMPLETE`.
3) The user is redirected to the SSR rendered questionnaire form and they fill it out and submit it. This populates the `questionnaire_form` field in the DB and sets the `status` field to `PENDING`.
4) A message is displayed telling the user when they can expect approval.
5) The user is redirected to the DANDI Archive homepage. The "LOG IN WITH GITHUB" button is now red and says something like "PENDING ACCOUNT APPROVAL". If the
user hasn't filled out the questionnaire yet, the button will say "COMPLETE SIGNUP PROCESS" and will redirect the user to the questionnaire form when clicked.
6) The DANDI admins will decide whether to approve or reject the user.
7) a) If approved, the user will receive an email saying so and they will be able to logon and use DANDI as normal.
   <br>
   b) If rejected, the user will receive an email containing the custom reason (if one was provided), as well as an email address to contact if they believe
   they shouldn't have been rejected.


### Proposed admin approval process
1) A user signs up as described in steps 1-4 in the previous section.
2) An email is sent to DANDI admins with a link to an SSR page that lists the user's info (name, email, GitHub account, etc) as well as their answers to the questionnaire. The page will contain two buttons - "APPROVE" or "REJECT" - and a textbox underneath the "REJECT" button entitled "Rejection Reason".
3)
    a) The admin decides to approve the user and clicks "APPROVE". This updates the user's `status` field to `APPROVED` and adds them to the `approved_users` group, granting them full access to DANDI.
    <br>
    b) The admin decides to reject the user, optionally fills out the "Rejection reason" box, and clicks "REJECT". This sets the user's `status` field to `REJECTED` and `is_active` field to `false`.

### Questionnaire
(from https://github.com/dandi/dandi-api/pull/454#issuecomment-892218858)
- What do you plan to use DANDI for?
- Any affiliations (university, company, etc)
