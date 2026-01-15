# Cell 5: Stitching Composites
import os
import cv2
import numpy as np
def stitch_composites(plants):
    for p,d in plants.items():
        comps = [d.get("composite")] if "composite" in d else []
        if not comps: continue
        stitched = comps[0]
        for nxt in comps[1:]:
            orb = cv2.ORB_create()
            k1,d1 = orb.detectAndCompute(stitched, None)
            k2,d2 = orb.detectAndCompute(nxt, None)
            if d1 is None or d2 is None: continue
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            m = sorted(bf.match(d1,d2), key=lambda x:x.distance)[:50]
            if len(m)<10: continue
            src = np.float32([k1[x.queryIdx].pt for x in m]).reshape(-1,1,2)
            dst = np.float32([k2[x.trainIdx].pt for x in m]).reshape(-1,1,2)
            M,_ = cv2.findHomography(dst,src,cv2.RANSAC,5.0)
            if M is None: continue
            h,w = stitched.shape[:2]
            warp = cv2.warpPerspective(nxt, M, (w+nxt.shape[1],h))
            stitched = np.maximum(stitched, warp[:h,:w])
        plants[p]["stitched"] = stitched
    return plants
