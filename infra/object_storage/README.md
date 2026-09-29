# Object storage

L'application ne parle qu'au protocole S3 (`django-storages[s3]`). Tout fournisseur compatible S3
convient ; changer de fournisseur, c'est migrer les objets et changer les variables `S3_*`.
Ce dossier contient la configuration à appliquer aux buckets, avec des commandes valables chez
n'importe quel fournisseur (AWS CLI).

## Deux buckets par environnement

| Bucket         | Storage Django | Accès                                                      |
|----------------|----------------|------------------------------------------------------------|
| `tpt-<env>-private` | `default` | URLs pré-signées, valables 5 min                            |
| `tpt-<env>-public`  | `public`  | ACL `public-read` posée sur chaque objet, URLs stables      |

Les review apps utilisent les buckets de staging, sous un préfixe à leur nom
(`techpourtoutes-staging-pr320/…`). À la fermeture de la PR, le workflow `review-app.yml` lance
`purge_review_app_files` sur la review app avant de la détruire.

Le dev local n'utilise aucun bucket : sans `S3_PRIVATE_BUCKET`, les fichiers vont dans `media/`,
et l'upload direct passe par la vue `create_local_upload`, qui imite le bucket. Tout marche hors
ligne.

## Configuration actuelle : OVHcloud

1. *Public Cloud* → *Object Storage* → *Utilisateurs Object Storage* : un utilisateur par
   environnement (`tpt-prod`, `tpt-staging`).
2. *Mes conteneurs* → *Créer un conteneur d'objets* : offre Standard (S3), 1-AZ, région GRA,
   Object Lock désactivé, chiffrement SSE-OMK, utilisateur de l'environnement lié. Versioning
   activé sur `tpt-prod-private` uniquement.
3. Profil AWS CLI (`aws --version` ≥ 2.23) :
   ```bash
   aws configure --profile tpt-staging          # clés de l'utilisateur, région gra
   aws configure set --profile tpt-staging endpoint_url https://s3.gra.io.cloud.ovh.net
   aws configure set --profile tpt-staging request_checksum_calculation when_required
   aws configure set --profile tpt-staging response_checksum_validation when_required
   ```
4. CORS, **avant** l'étape 5 (l'utilisateur restreint ne peut plus le modifier) :
   ```bash
   for b in tpt-staging-private tpt-staging-public; do
     aws s3api put-bucket-cors --profile tpt-staging --bucket $b \
       --cors-configuration file://infra/object_storage/cors_staging.json
   done
   ```
   En production : profil `tpt-prod`, buckets `tpt-prod-*`, fichier `cors.json`.
5. Restreindre l'utilisateur à ses buckets : *Utilisateurs Object Storage* → *…* → *Importer une
   politique JSON* → `user_policy.json`, en remplaçant `<ENV>` par `tpt-staging` ou `tpt-prod`.
   OVH ne supporte pas les bucket policies : la lecture publique passe par l'ACL des objets.
6. Variables d'environnement Scalingo :
   ```
   S3_ENDPOINT_URL=https://s3.gra.io.cloud.ovh.net
   S3_REGION=gra
   S3_ACCESS_KEY_ID=…
   S3_SECRET_ACCESS_KEY=…
   S3_PRIVATE_BUCKET=tpt-staging-private
   S3_PUBLIC_BUCKET=tpt-staging-public
   S3_PUBLIC_OBJECT_ACL=public-read
   ```
7. Vérifier : `scalingo --app <app> run python manage.py check_object_storage`. Pour chaque
   bucket, la commande écrit, relit, vérifie la lecture anonyme (refusée en privé, acceptée en
   public), vérifie qu'un upload pré-signé trop lourd est refusé, puis nettoie.

## Changer de fournisseur

- Recopier les objets (`rclone sync`), réappliquer le CORS, recréer les accès.
- Si le fournisseur ouvre le bucket public par une bucket policy plutôt que par ACL (AWS avec
  « Object Ownership: bucket owner enforced »), laisser `S3_PUBLIC_OBJECT_ACL` vide.
- Cloudflare R2 ne supporte pas l'upload par POST pré-signé : il faudrait adapter
  `CreatePresignedUpload`.
