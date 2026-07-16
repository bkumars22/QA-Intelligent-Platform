terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-south-1"
}

# ---- Kubernetes cluster for core services (always-on tier) ----
module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  cluster_name    = "qaip-core-cluster"
  cluster_version = "1.30"

  # Keep the node group small — core services are lightweight,
  # most of the compute-heavy work lives in Lambda now.
  eks_managed_node_groups = {
    core = {
      instance_types = ["t3.medium"]
      min_size       = 2
      max_size       = 6
      desired_size   = 3
    }
  }
}

# ---- Lambda for bursty AI inference (pay-per-use tier) ----
resource "aws_lambda_function" "ai_inference" {
  function_name = "qaip-ai-inference"
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.ai_inference.repository_url}:latest"
  role          = aws_iam_role.lambda_exec.arn

  memory_size = 1024
  timeout     = 60

  # Provisioned concurrency cuts cold starts for the first N
  # invocations during a burst — tune based on typical PR volume.
  reserved_concurrent_executions = 50

  environment {
    variables = {
      RISK_THRESHOLD      = "0.6"
      COST_TRACKER_TABLE  = aws_dynamodb_table.cost_tracker.name
    }
  }
}

resource "aws_lambda_event_source_mapping" "kafka_trigger" {
  event_source_arn = aws_msk_cluster.qaip_events.arn
  function_name    = aws_lambda_function.ai_inference.arn
  topics           = ["commit-events"]
  starting_position = "LATEST"
  batch_size        = 10
}

# ---- Managed Kafka for the event bus ----
resource "aws_msk_cluster" "qaip_events" {
  cluster_name           = "qaip-event-bus"
  kafka_version           = "3.7.0"
  number_of_broker_nodes  = 3

  broker_node_group_info {
    instance_type   = "kafka.t3.small"
    client_subnets  = module.vpc.private_subnets
    storage_info {
      ebs_storage_info {
        volume_size = 100
      }
    }
  }

  encryption_info {
    encryption_in_transit {
      client_broker = "TLS"
      in_cluster    = true
    }
  }
}

# ---- Data layer ----
resource "aws_db_instance" "postgres" {
  identifier             = "qaip-postgres"
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = "db.t3.medium"
  allocated_storage      = 50
  storage_encrypted      = true
  multi_az               = true
  backup_retention_period = 7
  deletion_protection    = true
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id      = "qaip-redis"
  engine          = "redis"
  node_type       = "cache.t3.micro"
  num_cache_nodes = 1
  engine_version  = "7.1"
}

resource "aws_dynamodb_table" "cost_tracker" {
  name         = "qaip-ai-cost-tracker"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "commit_sha"

  attribute {
    name = "commit_sha"
    type = "S"
  }
}

resource "aws_ecr_repository" "ai_inference" {
  name = "qaip-ai-inference"
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_iam_role" "lambda_exec" {
  name = "qaip-lambda-exec-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}
