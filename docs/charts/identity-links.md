# Cross-platform identity links

```mermaid
flowchart TD
    Action{"Dashboard action"}

    Action -->|"Link two identities"| Select["Load both canonical identities"]
    Select --> Distinct{"Different IDs?"}
    Distinct -->|"No"| Invalid["Reject with validation error"]
    Distinct -->|"Yes"| Exist{"Both identities exist?"}
    Exist -->|"No"| Missing["Return not found"]
    Exist -->|"Yes"| Owner{"Either is an owner identity?"}
    Owner -->|"Yes"| Conflict["Reject: owner accounts cannot be linked"]
    Owner -->|"No"| SameGroup{"Already in the same group?"}
    SameGroup -->|"Yes"| Idempotent["Return existing linked result"]
    SameGroup -->|"No"| Group["Reuse an existing group or create one"]
    Group --> Merge{"Both belong to different groups?"}
    Merge -->|"Yes"| Move["Move members into target group;<br/>remove old group"]
    Merge -->|"No"| Assign["Assign both identities to target group"]
    Move --> Assign
    Assign --> LinkEvent["Record linked event"]
    LinkEvent --> CommitLink["Commit transaction"]
    CommitLink -->|"Integrity conflict"| RollbackLink["Rollback and return conflict"]
    CommitLink -->|"Success"| Linked["Return linked result"]

    Action -->|"Unlink identity"| Load["Load canonical identity"]
    Load --> Exists{"Identity exists?"}
    Exists -->|"No"| Missing
    Exists -->|"Yes"| LinkedNow{"Currently grouped?"}
    LinkedNow -->|"No"| NotLinked["Return conflict: not linked"]
    LinkedNow -->|"Yes"| UnlinkEvent["Record unlinked event"]
    UnlinkEvent --> Clear["Remove identity from group"]
    Clear --> Members{"Fewer than two group members remain?"}
    Members -->|"Yes"| DeleteGroup["Clear remaining member and delete group"]
    Members -->|"No"| CommitUnlink["Commit transaction"]
    DeleteGroup --> CommitUnlink
    CommitUnlink -->|"Integrity conflict"| RollbackUnlink["Rollback and return conflict"]
    CommitUnlink -->|"Success"| Unlinked["Return unlinked result"]
```

Link requests reject the same identity twice, unknown IDs, and owner identities.
Linking two identities already in the same group is idempotent. When two
existing groups are joined, all members move to the target group before the old
group is removed. Unlink events are retained; a group with fewer than two
remaining members is dissolved.

Identity-link events are part of the analytics cache revision. The link or
unlink transaction commits the group changes and event together; integrity
errors roll back and return a conflict response.
