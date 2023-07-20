terraform {
  backend "s3" {
    key    = "domain_enumerator/terraform.tfstate"
  }
}