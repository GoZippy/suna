# Suna API Reference

This document provides comprehensive API documentation for the Suna self-hosted platform.

## 📋 API Overview

### Base URL
- **Development**: `http://localhost:8091`
- **Production**: `https://your-domain.com/api`

### Authentication
All API endpoints require authentication via JWT tokens, except for public endpoints.

### Response Format
All responses are in JSON format with the following structure:

```json
{
  "success": true,
  "data": {},
  "message": "Operation successful",
  "timestamp": "2024-12-01T10:00:00Z"
}
```

### Error Responses
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error description",
    "details": {}
  },
  "timestamp": "2024-12-01T10:00:00Z"
}
```

## 🔐 Authentication Endpoints

### POST /api/v1/auth/register
Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "secure_password",
  "first_name": "John",
  "last_name": "Doe",
  "organization": "Example Corp"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "user_123",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "organization": "Example Corp",
      "created_at": "2024-12-01T10:00:00Z"
    },
    "token": "jwt_token_here"
  },
  "message": "User registered successfully"
}
```

### POST /api/v1/auth/login
Authenticate user and get access token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "user_123",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "organization": "Example Corp",
      "tier": "pro",
      "created_at": "2024-12-01T10:00:00Z"
    },
    "token": "jwt_token_here",
    "refresh_token": "refresh_token_here"
  },
  "message": "Login successful"
}
```

### POST /api/v1/auth/refresh
Refresh access token using refresh token.

**Headers:**
```
Authorization: Bearer refresh_token_here
```

**Response:**
```json
{
  "success": true,
  "data": {
    "token": "new_jwt_token_here",
    "refresh_token": "new_refresh_token_here"
  },
  "message": "Token refreshed successfully"
}
```

### POST /api/v1/auth/logout
Logout user and invalidate tokens.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Response:**
```json
{
  "success": true,
  "message": "Logout successful"
}
```

### GET /api/v1/auth/me
Get current user information.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "user_123",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "organization": "Example Corp",
      "tier": "pro",
      "created_at": "2024-12-01T10:00:00Z",
      "last_login": "2024-12-01T10:00:00Z"
    }
  }
}
```

## 🤖 Agent Management Endpoints

### GET /api/v1/agents
List all agents for the current user.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `limit` (int): Items per page (default: 20)
- `status` (string): Filter by status (active, inactive, running)
- `search` (string): Search by name or description

**Response:**
```json
{
  "success": true,
  "data": {
    "agents": [
      {
        "id": "agent_123",
        "name": "Data Analysis Agent",
        "description": "Analyzes data and generates reports",
        "status": "active",
        "version": "1.0.0",
        "config": {
          "model": "gpt-4",
          "tools": ["web_search", "file_analysis"],
          "max_tokens": 4000
        },
        "created_at": "2024-12-01T10:00:00Z",
        "updated_at": "2024-12-01T10:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 50,
      "pages": 3
    }
  }
}
```

### POST /api/v1/agents
Create a new agent.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Request Body:**
```json
{
  "name": "Data Analysis Agent",
  "description": "Analyzes data and generates reports",
  "config": {
    "model": "gpt-4",
    "tools": ["web_search", "file_analysis"],
    "max_tokens": 4000,
    "temperature": 0.7
  },
  "version": "1.0.0"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "agent": {
      "id": "agent_123",
      "name": "Data Analysis Agent",
      "description": "Analyzes data and generates reports",
      "status": "active",
      "version": "1.0.0",
      "config": {
        "model": "gpt-4",
        "tools": ["web_search", "file_analysis"],
        "max_tokens": 4000,
        "temperature": 0.7
      },
      "created_at": "2024-12-01T10:00:00Z",
      "updated_at": "2024-12-01T10:00:00Z"
    }
  },
  "message": "Agent created successfully"
}
```

### GET /api/v1/agents/{agent_id}
Get agent details.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Response:**
```json
{
  "success": true,
  "data": {
    "agent": {
      "id": "agent_123",
      "name": "Data Analysis Agent",
      "description": "Analyzes data and generates reports",
      "status": "active",
      "version": "1.0.0",
      "config": {
        "model": "gpt-4",
        "tools": ["web_search", "file_analysis"],
        "max_tokens": 4000,
        "temperature": 0.7
      },
      "statistics": {
        "total_executions": 150,
        "successful_executions": 145,
        "average_execution_time": 45.2,
        "last_execution": "2024-12-01T09:30:00Z"
      },
      "created_at": "2024-12-01T10:00:00Z",
      "updated_at": "2024-12-01T10:00:00Z"
    }
  }
}
```

### PUT /api/v1/agents/{agent_id}
Update agent configuration.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Request Body:**
```json
{
  "name": "Updated Data Analysis Agent",
  "description": "Enhanced data analysis with better reporting",
  "config": {
    "model": "gpt-4-turbo",
    "tools": ["web_search", "file_analysis", "data_visualization"],
    "max_tokens": 8000,
    "temperature": 0.5
  },
  "version": "1.1.0"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "agent": {
      "id": "agent_123",
      "name": "Updated Data Analysis Agent",
      "description": "Enhanced data analysis with better reporting",
      "status": "active",
      "version": "1.1.0",
      "config": {
        "model": "gpt-4-turbo",
        "tools": ["web_search", "file_analysis", "data_visualization"],
        "max_tokens": 8000,
        "temperature": 0.5
      },
      "updated_at": "2024-12-01T11:00:00Z"
    }
  },
  "message": "Agent updated successfully"
}
```

### DELETE /api/v1/agents/{agent_id}
Delete an agent.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Response:**
```json
{
  "success": true,
  "message": "Agent deleted successfully"
}
```

### POST /api/v1/agents/{agent_id}/execute
Execute an agent with input data.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Request Body:**
```json
{
  "input": {
    "query": "Analyze the sales data for Q4 2024",
    "files": ["file_123", "file_124"],
    "parameters": {
      "analysis_type": "trend",
      "timeframe": "quarterly"
    }
  },
  "options": {
    "timeout": 300,
    "stream": false
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "execution_id": "exec_123",
    "status": "running",
    "agent": {
      "id": "agent_123",
      "name": "Data Analysis Agent"
    },
    "input": {
      "query": "Analyze the sales data for Q4 2024",
      "files": ["file_123", "file_124"],
      "parameters": {
        "analysis_type": "trend",
        "timeframe": "quarterly"
      }
    },
    "created_at": "2024-12-01T10:00:00Z"
  },
  "message": "Agent execution started"
}
```

### GET /api/v1/agents/{agent_id}/executions
Get agent execution history.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `limit` (int): Items per page (default: 20)
- `status` (string): Filter by status (running, completed, failed)
- `start_date` (string): Filter by start date (ISO format)
- `end_date` (string): Filter by end date (ISO format)

**Response:**
```json
{
  "success": true,
  "data": {
    "executions": [
      {
        "id": "exec_123",
        "status": "completed",
        "input": {
          "query": "Analyze the sales data for Q4 2024"
        },
        "output": {
          "result": "Sales analysis completed",
          "files": ["report_123.pdf"]
        },
        "execution_time": 45.2,
        "created_at": "2024-12-01T10:00:00Z",
        "completed_at": "2024-12-01T10:00:45Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 150,
      "pages": 8
    }
  }
}
```

## 🔄 Workflow Management Endpoints

### GET /api/v1/workflows
List all workflows for the current user.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `limit` (int): Items per page (default: 20)
- `status` (string): Filter by status (active, inactive, running)
- `search` (string): Search by name or description

**Response:**
```json
{
  "success": true,
  "data": {
    "workflows": [
      {
        "id": "workflow_123",
        "name": "Data Processing Pipeline",
        "description": "Automated data processing workflow",
        "status": "active",
        "steps": [
          {
            "id": "step_1",
            "name": "Data Collection",
            "agent_id": "agent_123",
            "order": 1,
            "config": {
              "input_mapping": {
                "query": "{{workflow.input.query}}"
              }
            }
          },
          {
            "id": "step_2",
            "name": "Data Analysis",
            "agent_id": "agent_124",
            "order": 2,
            "config": {
              "input_mapping": {
                "data": "{{step_1.output.result}}"
              }
            }
          }
        ],
        "triggers": [
          {
            "type": "schedule",
            "config": {
              "cron": "0 9 * * 1"
            }
          }
        ],
        "created_at": "2024-12-01T10:00:00Z",
        "updated_at": "2024-12-01T10:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 25,
      "pages": 2
    }
  }
}
```

### POST /api/v1/workflows
Create a new workflow.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Request Body:**
```json
{
  "name": "Data Processing Pipeline",
  "description": "Automated data processing workflow",
  "steps": [
    {
      "name": "Data Collection",
      "agent_id": "agent_123",
      "order": 1,
      "config": {
        "input_mapping": {
          "query": "{{workflow.input.query}}"
        }
      }
    },
    {
      "name": "Data Analysis",
      "agent_id": "agent_124",
      "order": 2,
      "config": {
        "input_mapping": {
          "data": "{{step_1.output.result}}"
        }
      }
    }
  ],
  "triggers": [
    {
      "type": "schedule",
      "config": {
        "cron": "0 9 * * 1"
      }
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "workflow": {
      "id": "workflow_123",
      "name": "Data Processing Pipeline",
      "description": "Automated data processing workflow",
      "status": "active",
      "steps": [
        {
          "id": "step_1",
          "name": "Data Collection",
          "agent_id": "agent_123",
          "order": 1,
          "config": {
            "input_mapping": {
              "query": "{{workflow.input.query}}"
            }
          }
        },
        {
          "id": "step_2",
          "name": "Data Analysis",
          "agent_id": "agent_124",
          "order": 2,
          "config": {
            "input_mapping": {
              "data": "{{step_1.output.result}}"
            }
          }
        }
      ],
      "triggers": [
        {
          "id": "trigger_1",
          "type": "schedule",
          "config": {
            "cron": "0 9 * * 1"
          }
        }
      ],
      "created_at": "2024-12-01T10:00:00Z",
      "updated_at": "2024-12-01T10:00:00Z"
    }
  },
  "message": "Workflow created successfully"
}
```

### GET /api/v1/workflows/{workflow_id}
Get workflow details.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Response:**
```json
{
  "success": true,
  "data": {
    "workflow": {
      "id": "workflow_123",
      "name": "Data Processing Pipeline",
      "description": "Automated data processing workflow",
      "status": "active",
      "steps": [
        {
          "id": "step_1",
          "name": "Data Collection",
          "agent_id": "agent_123",
          "order": 1,
          "config": {
            "input_mapping": {
              "query": "{{workflow.input.query}}"
            }
          }
        },
        {
          "id": "step_2",
          "name": "Data Analysis",
          "agent_id": "agent_124",
          "order": 2,
          "config": {
            "input_mapping": {
              "data": "{{step_1.output.result}}"
            }
          }
        }
      ],
      "triggers": [
        {
          "id": "trigger_1",
          "type": "schedule",
          "config": {
            "cron": "0 9 * * 1"
          }
        }
      ],
      "statistics": {
        "total_runs": 50,
        "successful_runs": 48,
        "average_duration": 120.5,
        "last_run": "2024-12-01T09:00:00Z"
      },
      "created_at": "2024-12-01T10:00:00Z",
      "updated_at": "2024-12-01T10:00:00Z"
    }
  }
}
```

### PUT /api/v1/workflows/{workflow_id}
Update workflow configuration.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Request Body:**
```json
{
  "name": "Updated Data Processing Pipeline",
  "description": "Enhanced automated data processing workflow",
  "steps": [
    {
      "name": "Data Collection",
      "agent_id": "agent_123",
      "order": 1,
      "config": {
        "input_mapping": {
          "query": "{{workflow.input.query}}"
        }
      }
    },
    {
      "name": "Data Analysis",
      "agent_id": "agent_124",
      "order": 2,
      "config": {
        "input_mapping": {
          "data": "{{step_1.output.result}}"
        }
      }
    },
    {
      "name": "Report Generation",
      "agent_id": "agent_125",
      "order": 3,
      "config": {
        "input_mapping": {
          "analysis": "{{step_2.output.result}}"
        }
      }
    }
  ],
  "triggers": [
    {
      "type": "schedule",
      "config": {
        "cron": "0 9 * * 1"
      }
    },
    {
      "type": "webhook",
      "config": {
        "url": "https://api.example.com/webhook"
      }
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "workflow": {
      "id": "workflow_123",
      "name": "Updated Data Processing Pipeline",
      "description": "Enhanced automated data processing workflow",
      "status": "active",
      "steps": [
        {
          "id": "step_1",
          "name": "Data Collection",
          "agent_id": "agent_123",
          "order": 1,
          "config": {
            "input_mapping": {
              "query": "{{workflow.input.query}}"
            }
          }
        },
        {
          "id": "step_2",
          "name": "Data Analysis",
          "agent_id": "agent_124",
          "order": 2,
          "config": {
            "input_mapping": {
              "data": "{{step_1.output.result}}"
            }
          }
        },
        {
          "id": "step_3",
          "name": "Report Generation",
          "agent_id": "agent_125",
          "order": 3,
          "config": {
            "input_mapping": {
              "analysis": "{{step_2.output.result}}"
            }
          }
        }
      ],
      "triggers": [
        {
          "id": "trigger_1",
          "type": "schedule",
          "config": {
            "cron": "0 9 * * 1"
          }
        },
        {
          "id": "trigger_2",
          "type": "webhook",
          "config": {
            "url": "https://api.example.com/webhook"
          }
        }
      ],
      "updated_at": "2024-12-01T11:00:00Z"
    }
  },
  "message": "Workflow updated successfully"
}
```

### DELETE /api/v1/workflows/{workflow_id}
Delete a workflow.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Response:**
```json
{
  "success": true,
  "message": "Workflow deleted successfully"
}
```

### POST /api/v1/workflows/{workflow_id}/execute
Execute a workflow manually.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Request Body:**
```json
{
  "input": {
    "query": "Process quarterly sales data",
    "parameters": {
      "quarter": "Q4",
      "year": "2024"
    }
  },
  "options": {
    "timeout": 600,
    "notify_on_completion": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "execution_id": "workflow_exec_123",
    "status": "running",
    "workflow": {
      "id": "workflow_123",
      "name": "Data Processing Pipeline"
    },
    "input": {
      "query": "Process quarterly sales data",
      "parameters": {
        "quarter": "Q4",
        "year": "2024"
      }
    },
    "created_at": "2024-12-01T10:00:00Z"
  },
  "message": "Workflow execution started"
}
```

## 📚 Knowledge Base Endpoints

### GET /api/v1/knowledge-base
List knowledge base documents.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `limit` (int): Items per page (default: 20)
- `search` (string): Search in document content
- `type` (string): Filter by document type (pdf, docx, txt, etc.)
- `tags` (string): Filter by tags (comma-separated)

**Response:**
```json
{
  "success": true,
  "data": {
    "documents": [
      {
        "id": "doc_123",
        "title": "Sales Report Q4 2024",
        "description": "Quarterly sales analysis and insights",
        "type": "pdf",
        "size": 2048576,
        "tags": ["sales", "quarterly", "analysis"],
        "uploaded_at": "2024-12-01T10:00:00Z",
        "updated_at": "2024-12-01T10:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 100,
      "pages": 5
    }
  }
}
```

### POST /api/v1/knowledge-base
Upload a document to the knowledge base.

**Headers:**
```
Authorization: Bearer jwt_token_here
Content-Type: multipart/form-data
```

**Form Data:**
- `file`: Document file
- `title`: Document title
- `description`: Document description
- `tags`: Comma-separated tags

**Response:**
```json
{
  "success": true,
  "data": {
    "document": {
      "id": "doc_123",
      "title": "Sales Report Q4 2024",
      "description": "Quarterly sales analysis and insights",
      "type": "pdf",
      "size": 2048576,
      "tags": ["sales", "quarterly", "analysis"],
      "file_path": "/storage/documents/doc_123.pdf",
      "uploaded_at": "2024-12-01T10:00:00Z",
      "updated_at": "2024-12-01T10:00:00Z"
    }
  },
  "message": "Document uploaded successfully"
}
```

### GET /api/v1/knowledge-base/{document_id}
Get document details.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Response:**
```json
{
  "success": true,
  "data": {
    "document": {
      "id": "doc_123",
      "title": "Sales Report Q4 2024",
      "description": "Quarterly sales analysis and insights",
      "type": "pdf",
      "size": 2048576,
      "tags": ["sales", "quarterly", "analysis"],
      "file_path": "/storage/documents/doc_123.pdf",
      "content_summary": "This document contains quarterly sales data...",
      "embeddings_generated": true,
      "uploaded_at": "2024-12-01T10:00:00Z",
      "updated_at": "2024-12-01T10:00:00Z"
    }
  }
}
```

### DELETE /api/v1/knowledge-base/{document_id}
Delete a document from the knowledge base.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Response:**
```json
{
  "success": true,
  "message": "Document deleted successfully"
}
```

### POST /api/v1/knowledge-base/search
Search knowledge base documents.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Request Body:**
```json
{
  "query": "sales performance Q4",
  "filters": {
    "tags": ["sales", "quarterly"],
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-12-31"
    }
  },
  "options": {
    "limit": 10,
    "include_content": true,
    "similarity_threshold": 0.7
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "document": {
          "id": "doc_123",
          "title": "Sales Report Q4 2024",
          "type": "pdf"
        },
        "relevance_score": 0.95,
        "matched_content": "Sales performance in Q4 2024 showed significant growth...",
        "page_number": 5
      }
    ],
    "total_results": 5,
    "search_time": 0.15
  }
}
```

## 📁 File Management Endpoints

### GET /api/v1/files
List uploaded files.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `limit` (int): Items per page (default: 20)
- `type` (string): Filter by file type
- `search` (string): Search by filename

**Response:**
```json
{
  "success": true,
  "data": {
    "files": [
      {
        "id": "file_123",
        "filename": "data.csv",
        "original_name": "sales_data.csv",
        "type": "csv",
        "size": 1048576,
        "uploaded_at": "2024-12-01T10:00:00Z",
        "url": "/api/v1/files/file_123/download"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 50,
      "pages": 3
    }
  }
}
```

### POST /api/v1/files/upload
Upload a file.

**Headers:**
```
Authorization: Bearer jwt_token_here
Content-Type: multipart/form-data
```

**Form Data:**
- `file`: File to upload

**Response:**
```json
{
  "success": true,
  "data": {
    "file": {
      "id": "file_123",
      "filename": "data.csv",
      "original_name": "sales_data.csv",
      "type": "csv",
      "size": 1048576,
      "uploaded_at": "2024-12-01T10:00:00Z",
      "url": "/api/v1/files/file_123/download"
    }
  },
  "message": "File uploaded successfully"
}
```

### GET /api/v1/files/{file_id}/download
Download a file.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Response:**
File content with appropriate headers.

### DELETE /api/v1/files/{file_id}
Delete a file.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Response:**
```json
{
  "success": true,
  "message": "File deleted successfully"
}
```

## 📊 Monitoring Endpoints

### GET /api/v1/monitoring/health
Get system health status.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "services": {
      "database": {
        "status": "healthy",
        "response_time": 0.05
      },
      "redis": {
        "status": "healthy",
        "response_time": 0.02
      },
      "ollama": {
        "status": "healthy",
        "response_time": 0.15
      }
    },
    "system": {
      "cpu_usage": 25.5,
      "memory_usage": 60.2,
      "disk_usage": 45.8
    },
    "timestamp": "2024-12-01T10:00:00Z"
  }
}
```

### GET /api/v1/monitoring/metrics
Get system metrics.

**Headers:**
```
Authorization: Bearer jwt_token_here
```

**Query Parameters:**
- `period` (string): Time period (1h, 24h, 7d, 30d)
- `metric` (string): Specific metric to retrieve

**Response:**
```json
{
  "success": true,
  "data": {
    "metrics": {
      "agent_executions": {
        "total": 1500,
        "successful": 1450,
        "failed": 50,
        "average_duration": 45.2
      },
      "workflow_runs": {
        "total": 300,
        "successful": 285,
        "failed": 15,
        "average_duration": 120.5
      },
      "system_performance": {
        "cpu_usage": [25.5, 30.2, 28.1],
        "memory_usage": [60.2, 65.8, 62.3],
        "disk_usage": [45.8, 46.2, 45.9]
      }
    },
    "period": "24h",
    "timestamp": "2024-12-01T10:00:00Z"
  }
}
```

## 🔧 Admin Endpoints

### GET /admin/dashboard
Get admin dashboard data.

**Headers:**
```
Authorization: Bearer admin_jwt_token_here
```

**Response:**
```json
{
  "success": true,
  "data": {
    "system_metrics": {
      "cpu_usage": 25.5,
      "memory_usage": 60.2,
      "disk_usage": 45.8,
      "network_io": {
        "bytes_sent": 1024000,
        "bytes_recv": 2048000
      }
    },
    "user_stats": {
      "total_users": 150,
      "active_users": 120,
      "new_users_today": 5
    },
    "agent_stats": {
      "total_agents": 50,
      "active_agents": 45,
      "executions_today": 150
    },
    "workflow_stats": {
      "total_workflows": 25,
      "active_workflows": 20,
      "runs_today": 30
    },
    "alerts": [
      {
        "id": "alert_1",
        "level": "warning",
        "message": "High memory usage detected",
        "timestamp": "2024-12-01T09:30:00Z"
      }
    ]
  }
}
```

### GET /admin/users
List all users (admin only).

**Headers:**
```
Authorization: Bearer admin_jwt_token_here
```

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `limit` (int): Items per page (default: 20)
- `status` (string): Filter by status (active, inactive)
- `tier` (string): Filter by tier (free, pro, enterprise)

**Response:**
```json
{
  "success": true,
  "data": {
    "users": [
      {
        "id": "user_123",
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "organization": "Example Corp",
        "tier": "pro",
        "status": "active",
        "created_at": "2024-12-01T10:00:00Z",
        "last_login": "2024-12-01T09:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 150,
      "pages": 8
    }
  }
}
```

### POST /admin/users
Create a new user (admin only).

**Headers:**
```
Authorization: Bearer admin_jwt_token_here
```

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "password": "secure_password",
  "first_name": "Jane",
  "last_name": "Smith",
  "organization": "Example Corp",
  "tier": "pro"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "user_124",
      "email": "newuser@example.com",
      "first_name": "Jane",
      "last_name": "Smith",
      "organization": "Example Corp",
      "tier": "pro",
      "status": "active",
      "created_at": "2024-12-01T10:00:00Z"
    }
  },
  "message": "User created successfully"
}
```

## 🚨 Error Codes

### Authentication Errors
- `AUTH_INVALID_CREDENTIALS`: Invalid email or password
- `AUTH_TOKEN_EXPIRED`: JWT token has expired
- `AUTH_TOKEN_INVALID`: Invalid JWT token
- `AUTH_INSUFFICIENT_PERMISSIONS`: User lacks required permissions

### Validation Errors
- `VALIDATION_ERROR`: Request validation failed
- `REQUIRED_FIELD_MISSING`: Required field is missing
- `INVALID_FORMAT`: Field format is invalid
- `FIELD_TOO_LONG`: Field exceeds maximum length

### Resource Errors
- `RESOURCE_NOT_FOUND`: Requested resource not found
- `RESOURCE_ALREADY_EXISTS`: Resource already exists
- `RESOURCE_IN_USE`: Resource is currently in use
- `RESOURCE_LIMIT_EXCEEDED`: Resource limit exceeded

### System Errors
- `INTERNAL_SERVER_ERROR`: Internal server error
- `SERVICE_UNAVAILABLE`: Service temporarily unavailable
- `DATABASE_ERROR`: Database operation failed
- `EXTERNAL_SERVICE_ERROR`: External service error

## 📝 Rate Limiting

API endpoints are rate-limited to prevent abuse:

- **Authentication endpoints**: 10 requests per minute
- **General endpoints**: 100 requests per minute
- **File upload endpoints**: 20 requests per minute
- **Admin endpoints**: 50 requests per minute

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## 🔒 Security

### Authentication
- All endpoints require JWT authentication (except public endpoints)
- Tokens expire after 24 hours
- Refresh tokens expire after 30 days

### Authorization
- Role-based access control (RBAC)
- User permissions are checked for each request
- Admin endpoints require admin privileges

### Data Protection
- All data is encrypted in transit (HTTPS)
- Sensitive data is encrypted at rest
- Input validation and sanitization on all endpoints

## 📚 SDK Examples

### Python SDK

```python
import suna

# Initialize client
client = suna.Client(
    base_url="https://your-domain.com/api",
    api_key="your_api_key"
)

# Create an agent
agent = client.agents.create(
    name="Data Analysis Agent",
    description="Analyzes data and generates reports",
    config={
        "model": "gpt-4",
        "tools": ["web_search", "file_analysis"]
    }
)

# Execute agent
execution = client.agents.execute(
    agent_id=agent.id,
    input={
        "query": "Analyze sales data for Q4 2024"
    }
)

# Get results
result = client.executions.get(execution.id)
print(result.output)
```

### JavaScript SDK

```javascript
import { SunaClient } from '@suna/sdk';

// Initialize client
const client = new SunaClient({
  baseUrl: 'https://your-domain.com/api',
  apiKey: 'your_api_key'
});

// Create an agent
const agent = await client.agents.create({
  name: 'Data Analysis Agent',
  description: 'Analyzes data and generates reports',
  config: {
    model: 'gpt-4',
    tools: ['web_search', 'file_analysis']
  }
});

// Execute agent
const execution = await client.agents.execute(agent.id, {
  input: {
    query: 'Analyze sales data for Q4 2024'
  }
});

// Get results
const result = await client.executions.get(execution.id);
console.log(result.output);
```

---

**API Version**: v1.0  
**Last Updated**: December 2024  
**Base URL**: `https://your-domain.com/api/v1`







