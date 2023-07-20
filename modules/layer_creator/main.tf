locals {
  layer_zip_path    = "${path.module}/layer.zip"
  layer_name        = var.layer_name
  requirements_path = "${path.root}/lambdas/requirements.txt"
}

# create zip file from requirements.txt. Triggers only when the file is updated
resource "null_resource" "lambda_layer" {
  triggers = {
    requirements = filesha1(local.requirements_path)
  }
  # the command to install python and dependencies to the machine and zips
  provisioner "local-exec" {
    command = <<EOT
      pip3 install -r ${local.requirements_path} -t ${path.module}/python/
      zip -r ${local.layer_zip_path} ${path.module}/python/
    EOT
  }
}

resource "aws_lambda_layer_version" "layer_package" {
  layer_name          = local.layer_name
  filename            = "${path.module}/layer.zip"
  compatible_runtimes = ["python3.9"]
  #skip_destroy = true
  depends_on = [null_resource.lambda_layer]
}
