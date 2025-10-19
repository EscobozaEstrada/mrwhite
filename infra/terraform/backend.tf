terraform {
    backend "s3" {
        bucket         = "monetizespirit-terraform-state-bucket"
        key            = "mrwhite/terraform.tfstate"
        region         = "us-east-1"
        encrypt        = true
        dynamodb_table = "monetizespirit-terraform-state-lock"
    }
}