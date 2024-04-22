terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }
  required_version = ">= 1.2.0"
}

provider "aws" {
  region = "us-east-1"
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
  ami                         = "ami-07761f3ae34c4478d"
  instance_type               = "t2.micro"
  key_name                    = "DullesXYZ_April_22_2024_KeyPair"
  associate_public_ip_address = true
  #  security_groups = ['web_server_sg_tf']
  vpc_security_group_ids      = [aws_security_group.web_server_sg_tf.id]
  user_data = <<EOF
    #!/bin/bash
    echo "Copying the SSH Key to the server"
    echo -e "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDEh3RV3GYJlW11pZj4Qz/D1xOGC6lspx6gICldQozkI/Uc9myU0VXs+jrwJ2/f3+WjO2Hgn9Dgve9MinIntOnka8df5+MnZ3a+1vBp29FI1SV7YZYDZI2HY6Sl59oWxMlv1/7I8C79h7h/0I4G1BulsX6OGxw6r8EEk28IxIKK5E8m1DgMkHGYLlruie1tqcj9/dNP8ID1drVfggwu4x/+EL+ynkTh1POb469wn8JoP2oOQUQGAsomLoa1DpXm6QJBdjjEMvlekf1wfPcAyr1I0x9tofKH0RmI1655psHT4wEl1hfIuXC9tR7aa64+maBhblEMtNHhBuXEla5FiDt2abWwD/JQw5IZ7ld3vbOoyHZGyIRa22bKUNe6QVKKtmuEmK4BUiPEqJ2AmLwtKQx+byTyOSYyQCngZ6nvfSpsKa21CzRaHjolb592Vjn//K0HXEcbDmiPfVGJNU/BMrwAFNz0RR0EBY9Kgc= esha@Esha-PC" >> /home/ec2-user/.ssh/authorized_keys
    chmod 600 /home/ec2-user/.ssh/authorized_keys
    eval `ssh-agent -s`
    EOF


  connection {
    type        = "ssh"
    user        = "ec2-user"
    private_key = file("/Users/shekar.lakshmipathi/Downloads/Firefox/DullesXYZ_April_22_2024_KeyPair.pem")
    host        = aws_instance.IADArrivServ.public_ip
  }

  provisioner "remote-exec" {
    inline = [
      "sudo yum update -y",
      "sudo yum install httpd git -y",
      "sudo systemctl restart httpd",
      "sudo systemctl enable httpd",
      "pip3 install requests pytz urllib3==1.26.6",
      "sudo chown ec2-user /var/www/html",
      "sudo chgrp ec2-user /var/www/html",
      "ssh-keygen -q -b 4096 -t rsa -N \"\" -f ~/.ssh/id_rsa",
      "eval \"$(ssh-agent -s)\"",
      "ssh-add ~/.ssh/id_rsa",
      "sudo timedatectl set-timezone America/New_York",
      "echo \"*/2 * * * * cd /home/ec2-user/dullesArrivals && git pull && /usr/bin/python3 getDullesArrivals.py && cp *.jpg /var/www/html && cp *.head.html /var/www/html && cp *.png /var/www/html && cp *.js /var/www/html  && cp *.css /var/www/html\" > mycron",
      "crontab mycron",
      "rm mycron"
    ]
  }

  tags = {
    Name = "DullesXYZ_EC2"
  }
}