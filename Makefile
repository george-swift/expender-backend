deploy-dev:
	$(MAKE) format
	chalice package --pkg-format terraform . --stage dev
	python3 scripts/patch_chalice_tf.py
	terraform apply -var-file=vars_dev.tfvars

deploy-prod:
	$(MAKE) format
	chalice package --pkg-format terraform . --stage prod
	python3 scripts/patch_chalice_tf.py
	terraform apply -var-file=vars_prod.tfvars

clean:
	rm -f chalice.tf.json deployment.zip layer-deployment.zip
	rm -rf .chalice/deployments/

format:
	black .
	isort .

.PHONY: deploy-dev deploy-prod clean format
