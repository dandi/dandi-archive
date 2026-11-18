# Add Admin Email Endpoint

## Summary

The goal is to add an API endpoint, accessible to admins only, that can send an email to a user

It could make sense to centralize ability to email DANDI users by use via API, so we could potentially use it in services outside of the dandi-archive, e.g. for admins

## Use Cases

- dandi-hub to notify users for home directories being reset, or excessive disk usage
- downtime notifications -- to all registered users
- validation errors reminders -- to corresponding authors of dandisets
- audit summaries -- to corresponding authors of dandisets

There could potentially be use cases even for authenticated users, although not immediately needed

Example:

    # Does not exist but could
    dandi-cli reportbug {dandiset_id}

## Background

We have 2 methods of sending emails right now:
 - Transactional emails, eg notifying a specific user during registration, are sent via Amazon SES
 - Broadcast emails, eg notifying all users, are sent via Mailchimp

Currently Mailchimp emails are done manually with their web GUI, but there is an API and emails
could be sent that way.

## Proposed design

For initial implementation, we propose a single new endpoint: `/api/users/mail/` with the following payload:
- subject
- message
- username
- content-encoding

This can make use of the existing SES infrastructure at `dandiapi/api/mail.py`, specifically `build_message`.

## Possible followups

We could also have a per dandiset endpoint `/dandisets/{dandiset__pk}/contact` which could send emails to the owners of the dandiset.

## Alternatives Considered

We have discussed the possibility of external services that use the mailchimp api directly, but this is not ideal because:
- Increased security surface area (spreading credentials)
- Increased duplication: each service that needs to use the endpoint will implement their own solution
