package example

# --- Basic allow/deny tests ---

test_allow_admin {
    allow with input as {"role": "admin", "action": "write"}
}

test_allow_user_read {
    allow with input as {"role": "user", "action": "read"}
}

test_deny_user_write {
    not allow with input as {"role": "user", "action": "write"}
}

test_deny_guest {
    not allow with input as {"role": "guest", "action": "read"}
}

# --- Edge case tests ---

# Explicitly verify the default-deny rule: a completely empty input object
# must be denied.  This is the most fundamental security property of the
# policy — it must hold even when no other rules fire.
test_default_deny_empty_input {
    not allow with input as {}
}

# Alias kept for backwards compatibility with any existing CI references.
test_deny_empty_input {
    not allow with input as {}
}

test_deny_missing_role {
    not allow with input as {"action": "read"}
}

test_deny_missing_action {
    not allow with input as {"role": "user"}
}

test_deny_empty_role {
    not allow with input as {"role": "", "action": "read"}
}

test_deny_null_role {
    not allow with input as {"role": null, "action": "read"}
}

test_deny_numeric_role {
    not allow with input as {"role": 123, "action": "read"}
}

test_deny_case_sensitive_role {
    not allow with input as {"role": "Admin", "action": "read"}
}

test_deny_case_sensitive_action {
    not allow with input as {"role": "user", "action": "Read"}
}

# --- Permissions tests ---

test_permissions_admin {
    perms := permissions with input as {"user": "admin", "resource": "doc-123"}
    count(perms) == 3
    "read" in perms
    "write" in perms
    "delete" in perms
}

test_permissions_user {
    perms := permissions with input as {"user": "alice", "resource": "doc-123"}
    count(perms) == 1
    "read" in perms
}

test_permissions_no_write_for_regular_user {
    perms := permissions with input as {"user": "alice", "resource": "doc-123"}
    not "write" in perms
    not "delete" in perms
}

test_permissions_empty_without_resource {
    perms := permissions with input as {"user": "alice"}
    count(perms) == 0
}

test_permissions_empty_without_user {
    perms := permissions with input as {"resource": "doc-123"}
    count(perms) == 0
}

test_permissions_empty_input {
    perms := permissions with input as {}
    count(perms) == 0
}
