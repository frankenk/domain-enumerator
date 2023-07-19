terraform {
  backend "s3" {
    key    = "domain_enumerator/terraform.tfstate"
    region = "eu-west-1"
  }
}