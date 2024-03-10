terraform {
 required_providers {
   aws = {
     source  = "hashicorp/aws"
     version = "~> 4.0"
   }
 }
}

provider "aws" {
 region = "us-east-1",
   "Parameters": {
    "TimeZone": "Australia/Sydney (AUS Eastern Standard Time)"
  }
}

data "aws_vpc" "default" {
 default = true
}

resource "aws_security_group" "web_server_sg_tf" {
 name        = "web-server-443-80-sg-tf"
 description = "Allow certain ports to EC2"
 vpc_id      = data.aws_vpc.default.id

ingress {
   description = "SSH"
   from_port   = 22
   to_port     = 22
   protocol    = "tcp"
   cidr_blocks = ["0.0.0.0/0"]
 }

ingress {
   description = "HTTP ingress"
   from_port   = 80
   to_port     = 80
   protocol    = "tcp"
   cidr_blocks = ["0.0.0.0/0"]
 }

ingress {
   description = "HTTPS ingress"
   from_port   = 443
   to_port     = 443
   protocol    = "tcp"
   cidr_blocks = ["0.0.0.0/0"]
 }

egress {
   from_port   = 0
   to_port     = 0
   protocol    = "-1"
   cidr_blocks = ["0.0.0.0/0"]
 }
}

resource "aws_instance" "IADArrivServ" {
  ami           = "ami-07761f3ae34c4478d"
  instance_type = "t2.micro"
  key_name      = "AWS_DullesXYZ_Feb26_2024"
  associate_public_ip_address = true
#  security_groups = ['web_server_sg_tf']
  vpc_security_group_ids      = [aws_security_group.web_server_sg_tf.id]

  connection {
    type = "ssh"
    user        = "ec2-user"
    private_key = file("/Users/shekar.lakshmipathi/Downloads/DullesXYZ_Feb26_2024_KeyPair.pem")
    host = aws_instance.IADArrivServ.public_ip
  }

 provisioner "remote-exec" {
    inline = [
      "sudo yum update -y",
      "sudo yum install httpd git -y",
      "sudo systemctl restart httpd",
      "sudo systemctl enable httpd",
      "ssh-keygen -q -b 4096 -t rsa -N \"\" -f ~/.ssh/id_rsa",
      "eval \"$(ssh-agent -s)\"",
      "ssh-add ~/.ssh/id_rsa",
      "sudo timedatectl set-timezone America/New_York"
    ]
  }

  tags = {
    Name = "DullesXYZ_EC2"
  }
}

