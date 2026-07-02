"""
Queries y mutations GraphQL de Jobber como constantes.
Validadas contra la API version 2025-01-20.
"""

# ── Clients ───────────────────────────────────────────────────────────────────

LIST_CLIENTS_QUERY = """
query ListClients {
  clients(first: 100) {
    nodes {
      id
      name
      companyName
      isCompany
    }
  }
}
"""

CREATE_CLIENT_MUTATION = """
mutation ClientCreate($input: ClientCreateInput!) {
  clientCreate(input: $input) {
    client {
      id
      name
      companyName
    }
    userErrors {
      message
      path
    }
  }
}
"""

# ── Properties ────────────────────────────────────────────────────────────────

FIND_PROPERTY_QUERY = """
query FindProperty($clientId: EncodedId!) {
  client(id: $clientId) {
    clientProperties(first: 100) {
      nodes {
        id
        address {
          street1
          street2
          city
          province
          postalCode
          country
        }
      }
    }
  }
}
"""

CREATE_PROPERTY_MUTATION = """
mutation PropertyCreate($clientId: EncodedId!, $input: PropertyCreateInput!) {
  propertyCreate(clientId: $clientId, input: $input) {
    properties {
      id
      address {
        street1
        city
      }
    }
    userErrors {
      message
      path
    }
  }
}
"""

# ── Jobs ──────────────────────────────────────────────────────────────────────

CREATE_JOB_MUTATION = """
mutation JobCreate($input: JobCreateAttributes!) {
  jobCreate(input: $input) {
    job {
      id
      jobNumber
      jobberWebUri
      visits(first: 1) {
        nodes {
          id
        }
      }
    }
    userErrors {
      message
      path
    }
  }
}
"""

VISIT_START_MUTATION = """
mutation VisitStart($visitId: EncodedId!) {
  visitStart(visitId: $visitId) {
    visit {
      id
    }
    userErrors {
      message
      path
    }
  }
}
"""

# ── Schema introspection (debug) ─────────────────────────────────────────────

INTROSPECT_TYPE_QUERY = """
query IntrospectType($typeName: String!) {
  __type(name: $typeName) {
    name
    kind
    inputFields {
      name
      type {
        name
        kind
        ofType {
          name
          kind
          ofType {
            name
            kind
          }
        }
      }
    }
    enumValues {
      name
    }
  }
}
"""

# ── Account ───────────────────────────────────────────────────────────────────

ACCOUNT_QUERY = """
query {
  account {
    id
    name
  }
}
"""
