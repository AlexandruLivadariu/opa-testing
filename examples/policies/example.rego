package example

# Simple allow/deny policy based on role
default allow = false

allow {
    input.role == "admin"
}

allow {
    input.role == "user"
    input.action == "read"
}

# Structured response with allowed and denied actions
permissions[action] {
    input.user
    input.resource
    action := "read"
}

permissions[action] {
    input.user == "admin"
    input.resource
    action := "write"
}

permissions[action] {
    input.user == "admin"
    input.resource
    action := "delete"
}
