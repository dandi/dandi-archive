# Premise
Currently, anyone with a GitHub account can signup for DANDI and make full use of its functionality. The goal of this design document is to introduce an
approval process to help prevent misuse of the archive.

## 1. Implementation Details
### Changes to User model
A new model*, `UserMetadata`, will be introduced. This model will have a foreign key reference (one-to-one relationship) with each `User`.
In addition to the `User` foreign key, `UserMetadata` will contain three columns: `status`, `questionnaire_form`, and `rejection_reason`.
- `status` is an enum that can be one of four values: `INCOMPLETE`, `PENDING`, `APPROVED`, or `REJECTED`.
- `questionnaire_form` is a JSON field. The keys are questions, and the values are the users' answers.
- `rejection_reason` is an optional string that contains a message written by one of the admins describing why a user was denied approval (if applicable)

\* Why create a new model? https://docs.djangoproject.com/en/3.2/topics/auth/customizing/#extending-the-existing-user-model

### Changes to API
- /users/me needs to include the user's current status
- Only users with a status of `APPROVED` will have access to protected endpoints.
  - This will be done through two new permission classes: `isApproved` and `isApprovedOrReadonly`, which will be similar to DRF's `isAuthenticated` and `isAuthenticatedOrReadonly` with an added check to see if the user is `APPROVED`.
- Only approved users can create and edit dandisets.
- /users/search endpoint will only return users with a status of `APPROVED`.

### Changes to frontend
- Configuration so the frontend knows where to find SSR pages
- If a user is pending approval or rejected, a banner will be shown in the UI alerting them of their current status.

### New views
- SSR rendered pages for questionnaire form, pending approval page, rejected page, and admin approval page.

## 2. High-level Overview
### Current user signup flow
1) The user navigates to https://gui.dandiarchive.org and clicks the "LOG IN WITH GITHUB" button
2) The user is redirected to GitHub, enters their credentials, and clicks "Sign in". This action creates a new DANDI Archive account for the user and gives
them full capabilities of any other normal user (creating/editing dandisets, etc).
3) An email is sent to the user confirming their registration.
4) The user is redirected back to https://gui.dandiarchive.org signed in to their new account.

### Proposed user signup flow
1) The user navigates to https://gui.dandiarchive.org and clicks the "LOG IN WITH GITHUB" button.
2) The user is redirected to GitHub, enters their credentials, and clicks "Sign in". This action creates a new DANDI Archive account for the user with the `status` field set to `INCOMPLETE`.
3) The user is redirected to the SSR rendered questionnaire form and they fill it out and submit it. This populates the `questionnaire_form` field in the DB and sets the `status` field to `PENDING`.
4) An email is sent to the user confirming their registration and telling them when they can expect approval.
5) The user is redirected to the DANDI Archive homepage. A banner will be displayed underneath the navbar telling the user that their account is pending approval.
6) The DANDI admins will decide whether to approve or reject the user.
7) a) If approved, the user will receive an email saying so and they will be able to logon and use DANDI as normal.
   <br>
   b) If rejected, the user will receive an email containing the custom reason (if one was provided), as well as an email address to contact if they believe they shouldn't have been rejected. If the user attempts to login again, they will be placed into a "read-only" mode with a red banner underneath the navbar in the web UI that tells them their account has been rejected.


### Proposed admin approval process
1) A user signs up as described in steps 1-4 in the previous section.
2) An email is sent to DANDI admins with a link to an SSR page that lists the user's info (name, email, GitHub account, etc), their current `status`, as well as their answers to the questionnaire. The page will contain two buttons - "APPROVE" or "REJECT" - and a textbox underneath the "REJECT" button entitled "Rejection Reason".
3)
    a) The admin decides to approve the user and clicks "APPROVE". This updates the user's `status` field to `APPROVED`, granting them full access to DANDI.
    <br>
    b) The admin decides to reject the user, optionally fills out the "Rejection reason" box, and clicks "REJECT". This sets the user's `status` field to `REJECTED` and sets their `is_active` field to `False`.

### Questionnaire
(from https://github.com/dandi/dandi-api/pull/454#issuecomment-892218858)
- What do you plan to use DANDI for?
- Any affiliations (university, company, etc)
