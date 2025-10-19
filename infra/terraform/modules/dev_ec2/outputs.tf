# modules/dev_ec2/outputs.tf
# Outputs from Developer EC2 module

output "instance_id" {
  description = "ID of the developer EC2 instance"
  value       = aws_instance.dev_workstation.id
}

output "instance_public_ip" {
  description = "Public IP address of the developer EC2 instance"
  value       = aws_instance.dev_workstation.public_ip
}

output "instance_public_dns" {
  description = "Public DNS name of the developer EC2 instance"
  value       = aws_instance.dev_workstation.public_dns
}

output "security_group_id" {
  description = "ID of the security group attached to the instance"
  value       = aws_security_group.dev_instance.id
}

output "iam_role_arn" {
  description = "ARN of the IAM role attached to the instance"
  value       = aws_iam_role.dev_instance.arn
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i ~/.ssh/${var.key_name}.pem ubuntu@${aws_instance.dev_workstation.public_ip}"
}

output "auto_stop_alarm_arn" {
  description = "ARN of the auto-stop CloudWatch alarm"
  value       = aws_cloudwatch_metric_alarm.auto_stop.arn
}

output "connection_info" {
  description = "Connection information for the developer workstation"
  value = {
    instance_id  = aws_instance.dev_workstation.id
    public_ip    = aws_instance.dev_workstation.public_ip
    ssh_command  = "ssh -i ~/.ssh/${var.key_name}.pem ubuntu@${aws_instance.dev_workstation.public_ip}"
    auto_stop    = "Instance will auto-stop after ${var.auto_stop_evaluation_periods * 10} minutes of CPU < ${var.auto_stop_cpu_threshold}%"
    secrets_path = var.ssm_parameter_path
  }
}
